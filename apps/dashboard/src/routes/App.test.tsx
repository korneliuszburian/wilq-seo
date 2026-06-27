import { readFileSync } from "node:fs";

import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { QueryClient } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ConnectorRefreshRun } from "../lib/api";
import { App, createWilqQueryClient, createWilqRouter } from "./App";
import { ConnectorRefreshRunList } from "./RegistryPanels";

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

function customSegmentSafetyReview(previewId: string) {
  return {
    id: `${previewId}_safety`,
    custom_segment_preview_id: previewId,
    safety_contract: "custom_segment_apply_safety_v1",
    status: "blocked",
    reason:
      "Zapis segmentu niestandardowego zablokowany: podgląd jest do sprawdzenia.",
    missing_requirements: [
      "forecast_or_audience_size",
      "google_ads_mutation_audit",
      "human_confirm_before_apply"
    ],
    required_validation: [
      "review_source_terms",
      "reject_brand_or_low_intent_terms",
      "keyword_planner_enrichment",
      "forecast_or_audience_size",
      "custom_segment_operation_preview",
      "google_ads_mutation_audit",
      "human_confirm_before_apply"
    ],
    blocked_claims: [
      "rozmiar odbiorców",
      "wzrost konwersji",
      "zwrot z reklam",
      "zapis kierowania reklam",
      "skuteczność kampanii"
    ],
    evidence_ids: ["ev_refresh_refresh_google_ads_test"],
    audit_required: true,
    api_mutation_ready: false,
    apply_allowed: false,
    destructive: false
  };
}

const opportunities = [
  {
    id: "opp_decision_review_ads_campaign_metrics",
    type: "google_ads_review_queue",
    title: "Przejrzyj kolejki Ads do sprawdzenia bez zapisu zmian",
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
      "Google Ads ma liczniki do oceny i akcje do sprawdzenia. Zapis pozostaje zablokowany.",
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
    evidence_ids: [
      "ev_refresh_merchant_feed",
      "ev_refresh_merchant_issue_clusters",
      "ev_refresh_merchant_safety"
    ],
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
    review_gate: {
      status: "pending_validation",
      summary: "Wymaga sprawdzenia w WILQ; zapis zmian pozostaje zablokowany osobnymi warunkami.",
      required_checks: [
        "identify_disapproved_products",
        "group_issue_reasons",
        "require_human_confirm_before_apply"
      ],
      required_check_labels: [
        "rozpoznaj produkty odrzucone w Merchant Center",
        "pogrupuj powody problemów feedu",
        "potwierdzenie człowieka przed zapisem"
      ],
      operator_checklist: [
        "identify_disapproved_products",
        "group_issue_reasons",
        "require_human_confirm_before_apply"
      ],
      operator_checklist_labels: [
        "rozpoznaj produkty odrzucone w Merchant Center",
        "pogrupuj powody problemów feedu",
        "potwierdzenie człowieka przed zapisem"
      ],
      apply_blockers: [
        "action_mode_prepare_only",
        "action_validation_required",
        "payload_apply_allowed_false",
        "human_confirm_before_apply"
      ],
      apply_blocker_labels: [
        "tryb przygotowania bez zapisu zmian",
        "wymagane sprawdzenie w WILQ",
        "podgląd zmian nie pozwala na zapis",
        "potwierdzenie człowieka przed zapisem"
      ],
      confirmation_required: true,
      apply_allowed: false,
      last_mutation_audit_id: "mutation_act_review_merchant_feed_issues_test",
      last_mutation_audit_status: "blocked",
      last_mutation_audit_actor: "operator_local_dashboard",
      last_mutation_audit_at: "2026-06-17T10:03:00Z",
      last_mutation_audit_summary:
        "Zmiana zablokowana przed wywołaniem zewnętrznego systemu. Blockers: Vendor mutation adapter is not implemented for this action.",
      last_mutation_attempted: false,
      last_mutation_adapter: null,
      last_mutation_audit_event_id: "audit_act_review_merchant_feed_issues_apply_test",
      last_mutation_blockers: ["vendor_mutation_adapter_required"],
      last_mutation_blocker_labels: ["brak bezpiecznej ścieżki zapisu w zewnętrznym systemie"]
    },
    human_diagnosis: "Merchant Center ma realne metryki produktu/feedu w WILQ.",
    recommended_reason: "Przygotuj kolejkę problemów feedu z podglądem zmian.",
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
      preview_contract: "ga4_tracking_quality_review_v1",
      payload_preview: [
        {
          id: "ga4_tracking_review_fixture",
          preview_contract: "ga4_tracking_quality_review_v1",
          operation_type: "tracking_quality_review",
          landing_page: "/oferta/",
          source_medium: "google / cpc",
          campaign_name: "(2026) Ekologus Ogólna",
          tracking_dimension_gaps: [],
          metric_snapshot: {
            active_users: 20,
            sessions: 30
          },
          metric_snapshot_labels: {
            active_users: "aktywni użytkownicy",
            sessions: "sesje"
          },
          reason:
            "Lista sprawdzenia strony wejścia, źródła ruchu i kampanii do oceny jakości ruchu. To nie odblokowuje zwrotu z reklam ani przychodów.",
          required_validation: [
            "review_landing_page_dimension",
            "review_source_medium_dimension",
            "review_campaign_name_dimension",
            "review_conversion_or_key_event_mapping",
            "human_confirm_before_tracking_change"
          ],
          blocked_claims: ["współczynnik konwersji", "zwrot z reklam", "przychód"],
          evidence_ids: ["ev_refresh_ga4"],
          api_mutation_ready: false,
          apply_allowed: false,
          destructive: false
        }
      ],
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
    human_diagnosis: "Spis treści WordPress można zestawić z GSC przed tworzeniem nowych tematów.",
    recommended_reason: "Przygotuj kolejkę: zachować, odświeżyć, scalić, utworzyć albo zablokować.",
    payload: {
      action_type: "wordpress_content_refresh",
      connector: "wordpress_ekologus",
      mode: "prepare_only",
      preview_contract: "content_brief_preview_v1",
      content_brief_preview: [
        {
          preview_contract: "content_brief_preview_v1",
          candidate_id: "content_brief_gsc_zielony_lad",
          source_type: "gsc_query_page",
          mode: "refresh",
          topic: "zielony ład",
          target_url: "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/",
          wordpress_inventory_match: "present",
          decision_option_labels: [
            "odśwież istniejącą treść",
            "scal z istniejącą treścią",
            "zablokuj"
          ],
          gsc_demand: "present",
          metric_snapshot: {
            clicks: 12,
            impressions: 120,
            ctr: 0.1
          },
          brief_goal:
            "Przygotuj plan odświeżenia albo scalenia istniejącej treści pod temat `zielony ład`.",
          content_angle:
            "Odśwież istniejącą treść wokół intencji zielony ład bez obietnic pozycji.",
          audience: "Decydent środowiskowy szukający prostego wyjaśnienia regulacji.",
          key_objections: ["czy tekst jest aktualny prawnie", "czy nie dubluje innej strony"],
          h1_direction: "H1 ma jasno odpowiedzieć na intencję zielony ład.",
          h2_direction: ["czym jest Zielony Ład", "wpływ na firmę"],
          faq_direction: ["Co oznacza Zielony Ład dla firmy?"],
          cta_direction: "CTA do rozmowy o wpływie regulacji na firmę.",
          internal_link_direction: ["powiązane treści o regulacjach środowiskowych"],
          source_facts: ["GSC page=/europejski-zielony-lad-co-to-takiego/", "clicks=12"],
          missing_evidence: ["brak dowodu wzrost liczby leadów"],
          forbidden_claims: ["wzrost liczby leadów", "wpływ na przychód", "gwarancja pozycji"],
          publication_blocker_labels: [
            "potwierdzenie publicznego URL-a",
            "kontrola duplikacji i kanibalizacji",
            "potwierdzenie człowieka przed zapisem WordPress"
          ],
          required_validation: [
            "wordpress_existing_url_confirmed",
            "gsc_query_page_check",
            "duplicate_or_cannibalization_check",
            "human_confirm_before_wordpress_write"
          ],
          required_validation_labels: [
            "istniejący URL potwierdzony w WordPress",
            "sprawdzenie zapytań i URL-i z GSC",
            "kontrola duplikacji i kanibalizacji",
            "potwierdzenie człowieka przed zapisem WordPress"
          ],
          blocked_claims: ["wzrost liczby leadów", "wpływ na przychód", "gwarancja pozycji"],
          evidence_ids: ["ev_refresh_gsc"],
          source_connectors: ["google_search_console", "wordpress_ekologus"],
          apply_allowed: false,
          api_mutation_ready: false,
          destructive: false
        },
        {
          preview_contract: "content_brief_preview_v1",
          candidate_id: "content_brief_ahrefs_audyt_srodowiskowy",
          source_type: "ahrefs_gap_review",
          mode: "review",
          topic: "audyt środowiskowy",
          source_url: "https://www.denios.pl/audyt-srodowiskowy/",
          competitor_domain: "denios.pl",
          wordpress_inventory_match: "unknown",
          gsc_demand: "unknown",
          metric_snapshot: {
            metric_name: "ahrefs_content_gap_count",
            metric_value: 1
          },
          decision_option_labels: [
            "odśwież istniejącą treść",
            "scal z istniejącą treścią",
            "utwórz po kontroli",
            "zablokuj"
          ],
          brief_goal:
            "Zweryfikuj temat z Ahrefs przeciw GSC i WordPress, zanim powstanie plan treści.",
          required_validation: [
            "business_relevance_review",
            "gsc_demand_check",
            "wordpress_inventory_check",
            "duplicate_or_cannibalization_check"
          ],
          blocked_claims: ["wzrost ruchu", "wzrost autorytetu", "gwarancja pozycji"],
          evidence_ids: ["ev_refresh_ahrefs_gap_records"],
          source_connectors: ["ahrefs"],
          apply_allowed: false,
          api_mutation_ready: false,
          destructive: false
        }
      ],
      wordpress_draft_payload_preview: [
        {
          preview_contract: "wordpress_draft_payload_preview_v1",
          source_preview_contract: "content_brief_preview_v1",
          candidate_id: "content_brief_gsc_zielony_lad",
          source_type: "gsc_query_page",
          mode: "refresh",
          connector: "wordpress_ekologus",
          operation_type: "prepare_existing_content_draft",
          post_status: "draft",
          topic: "zielony ład",
          target_url: "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/",
          content_gate_status_summary: [
            "spis treści: spis potwierdzony na obecnej stronie",
            "URL kanoniczny: obecny URL potwierdzony",
            "duplikaty: odśwież albo scal zamiast pisać od nowa"
          ],
          draft_blocker_labels: [
            "kontrola URL-a kanonicznego",
            "kontrola duplikacji i kanibalizacji"
          ],
          draft_generation_summary: [
            "wynik: plan treści do czasu kontroli",
            "warunek: dowody są podpięte"
          ],
          draft_readiness_review_summary: [
            "szkic: trzeba rozstrzygnąć duplikację",
            "człowiek: zapisano ocenę przygotowania"
          ],
          draft_readiness_review_contract_summary: [
            "wymaga: wynik decyzji człowieka",
            "blokuje: zapis szkicu WordPress"
          ],
          wordpress_draft_handoff_summary: [
            "status: zablokowany do przejścia kontroli szkicu",
            "blokada: kontrola duplikacji i kanibalizacji"
          ],
          wordpress_draft_handoff_contract_summary: [
            "warunek: kontrola duplikacji i kanibalizacji",
            "blokuje: publikacja WordPress"
          ],
          post_publication_measurement_summary: [
            "status: zablokowany do publikacji i danych po publikacji",
            "sprawdzenie: 28 dni po publikacji"
          ],
          draft_payload: {
            post_status: "draft",
            post_title: "Odświeżenie: zielony ład",
            post_excerpt_direction:
              "Przygotuj plan odświeżenia albo scalenia istniejącej treści pod temat `zielony ład`.",
            content_blocks: [
              {
                section: "intent",
                instruction: "Opisz intencję użytkownika."
              },
              {
                section: "title_h1",
                instruction: "Zaproponuj kierunek title/H1."
              }
            ]
          },
          required_validation: [
            "operator_review_approved_for_prepare",
            "wordpress_existing_url_confirmed",
            "human_confirm_before_wordpress_write"
          ],
          required_validation_labels: [
            "operator zatwierdził przygotowanie",
            "istniejący URL potwierdzony w WordPress",
            "potwierdzenie człowieka przed zapisem WordPress"
          ],
          blocked_claims: ["wzrost liczby leadów", "wpływ na przychód", "gwarancja pozycji"],
          source_connectors: ["google_search_console", "wordpress_ekologus"],
          evidence_ids: ["ev_refresh_gsc"],
          mutation_allowed: false,
          apply_allowed: false,
          api_mutation_ready: false,
          destructive: false
        }
      ],
      destructive: false
    },
    audit_events: []
  },
  {
    id: "act_prepare_negative_keyword_review_queue",
    title: "Przygotuj kolejkę review wykluczeń z listy wyszukiwanych haseł",
    domain: "google_ads",
    connector: "google_ads",
    mode: "prepare",
    risk: "medium",
    status: "needs_validation",
    evidence_ids: ["ev_refresh_refresh_google_ads_test"],
    metrics: [],
    validation_status: "not_validated",
    human_diagnosis:
      "Google Ads ma search-term metryki do review, ale apply wymaga 90-day safety check.",
    recommended_reason: "Przygotuj kolejkę do sprawdzenia bez obietnic o marnowaniu budżetu.",
    payload: {
      action_type: "negative_keyword_candidate",
      connector: "google_ads",
      mode: "prepare_only",
      terms: ["odpady cena"],
      evidence_ids: ["ev_refresh_refresh_google_ads_test"],
      preview_contract: "negative_keyword_change_preview_v1",
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
          blocked_claims: ["dodanie wykluczających słów kluczowych", "marnowanie budżetu na zapytaniach"],
          api_mutation_ready: false,
          apply_allowed: false,
          destructive: false
        }
      ],
      required_validation: [
        "90_day_safety_check",
        "negative_keyword_change_preview"
      ],
      apply_allowed: false,
      destructive: false
    },
    audit_events: []
  },
  {
    id: "act_prepare_google_ads_recommendation_review_queue",
    title: "Przygotuj ocenę rekomendacji Google Ads",
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
    recommended_reason: "Sprawdź typ rekomendacji i podgląd wpływu bez zapisu zmian.",
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
          blocked_claims: ["zapis rekomendacji"],
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
          reason: "Podgląd zmian dla rekomendacji Google Ads jest do sprawdzenia w WILQ.",
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
            "zapis rekomendacji",
            "automatyczne przyjęcie rekomendacji",
            "zmiana budżetu",
            "zapis zmian kampanii",
            "obietnica poprawy wyniku"
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
        "zapis rekomendacji",
        "automatyczne przyjęcie rekomendacji",
        "zmiana budżetu",
        "zapis zmian kampanii",
        "obietnica poprawy wyniku"
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
    summary: "Google Ads ma braki dostępu.",
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
] satisfies ConnectorRefreshRun[];

const adsDiagnostics = {
  generated_at: "2026-06-17T10:00:00Z",
  language: "pl-PL",
  strict_instruction: "WILQ pokazuje tylko metryki z danych źródłowych.",
  connector_status_label: "dostęp skonfigurowany",
  latest_refresh_status_label: "zakończony",
  live_data_status_label: "metryki Google Ads dostępne",
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
    summary: "Odczyt Google Ads zakończony przez googleAds:searchStream. Wiersze kampanii: 18.",
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
      "WILQ ma 1 wierszy kampanii: kliknięcia=107, wyświetlenia=2783, koszt=164,59 zł, konwersje=2.5, wartość konwersji=450.75.",
    allowed_metrics: ["clicks", "impressions", "cost_micros", "conversions", "conversion_value"],
    missing_read_contracts: [],
    blocked_claims: ["koszt pozyskania celu", "zwrot z reklam", "marnowanie budżetu na zapytaniach", "zmarnowany budżet"],
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
        blocked_claims: ["koszt pozyskania celu", "zwrot z reklam", "marnowanie budżetu na zapytaniach", "zmarnowany budżet"]
      }
    ],
    next_step: "Użyj wierszy kampanii do sprawdzenia aktywności."
  },
  account_currency_read_contract: {
    id: "ads_account_currency_read_contract",
    status: "ready",
    title: "Google Ads: waluta konta",
    summary: "WILQ ma walutę konta Google Ads z evidence: PLN.",
    currency_code: "PLN",
    allowed_metrics: ["account_currency_code"],
    missing_read_contracts: [],
    blocked_claims: ["opłacalność", "ocena marży", "zmiana budżetu"],
    source_connectors: ["google_ads"],
    evidence_ids: ["ev_refresh_refresh_google_ads_test"],
    next_step:
      "Pokazuj koszt, CPC i CPA w walucie konta. Nadal nie oceniaj rentowności bez marży, celu biznesowego i sprawdzonego podglądu."
  },
  business_context_read_contract: {
    id: "ads_business_context_read_contract",
    status: "blocked",
    title: "Google Ads: kontekst biznesowy decyzji",
    summary:
      "WILQ ma live metryki Google Ads, ale nie ma kompletnego lokalnego kontekstu biznesowego.",
    profit_margin: null,
    business_goal: null,
    budget_goal: null,
    target_roas: null,
    target_cpa_micros: null,
    strategy_review_status: "missing",
    strategy_reviewed_by: null,
    strategy_reviewed_at: null,
    strategy_review_summary: null,
    configured_sources: [],
    business_policy_ids: ["complete_business_context_before_ads_verdicts"],
    operator_review_gates: [
      "human_strategy_review",
      "configure_profit_margin_or_value_model",
      "configure_business_goal",
      "configure_human_budget_goal",
      "confirm_target_roas_or_cpa"
    ],
    target_interpretation: {
      id: "ads_business_target_interpretation",
      interpretation_contract: "ads_business_target_interpretation_v1",
      status: "blocked",
      status_label: "zablokowane",
      summary:
        "WILQ nie interpretuje KPI biznesowo, dopóki brakuje marży, celu biznesowego albo celu budżetu.",
      allowed_uses: [],
      allowed_use_labels: [],
      blocked_uses: [
        "profitability_verdict",
        "target_kpi_verdict",
        "budget_scaling",
        "budget_apply",
        "wasted_budget_claim"
      ],
      blocked_use_labels: [
        "ocena opłacalności",
        "ocena wskaźników względem celu",
        "skalowanie budżetu",
        "zmiana budżetu",
        "wniosek o zmarnowanym budżecie"
      ],
      missing_requirements: [
        "profit_margin",
        "business_goal",
        "human_budget_goal",
        "target_roas_or_cpa",
        "human_strategy_review"
      ],
      missing_requirement_labels: [
        "marża albo model rentowności",
        "cel biznesowy",
        "cel budżetu od człowieka",
        "docelowy zwrot z reklam albo koszt pozyskania celu",
        "ocena strategii przez człowieka"
      ],
      required_validation: [
        "review_profit_margin_model",
        "review_business_goal",
        "review_human_budget_goal",
        "confirm_target_roas_or_cpa",
        "human_strategy_review"
      ],
      required_validation_labels: [
        "sprawdzenie modelu marży",
        "sprawdzenie celu biznesowego",
        "sprawdzenie celu budżetu",
        "potwierdzenie docelowego zwrotu z reklam albo kosztu pozyskania celu",
        "ocena strategii przez człowieka"
      ],
      policy_ids: ["complete_business_context_before_ads_verdicts"],
      evidence_ids: ["ev_refresh_refresh_google_ads_test"],
      action_ids: ["act_configure_ads_business_context"],
      apply_allowed: false,
      destructive: false
    },
    strategy_review_readiness_contract: {
      id: "ads_strategy_review_readiness_contract",
      status: "blocked",
      status_label: "zablokowane",
      title: "Google Ads: gotowość oceny strategii przez człowieka",
      summary:
        "Ocena strategii Ads przez człowieka nie jest zatwierdzona, więc WILQ może tylko przygotować kolejki oceny.",
      latest_review_status: "missing",
      latest_review_status_label: "brak oceny",
      latest_review_outcome: null,
      reviewed_by: null,
      reviewed_at: null,
      current_context: {
        profit_margin: null,
        business_goal: null,
        budget_goal: null,
        target_roas: null,
        target_cpa_micros: null
      },
      required_validation: [
        "review_profit_margin_model",
        "review_business_goal",
        "review_human_budget_goal",
        "confirm_target_roas_or_cpa",
        "human_strategy_review"
      ],
      required_validation_labels: [
        "sprawdzenie modelu marży",
        "sprawdzenie celu biznesowego",
        "sprawdzenie celu budżetu",
        "potwierdzenie docelowego zwrotu z reklam albo kosztu pozyskania celu",
        "ocena strategii przez człowieka"
      ],
      missing_read_contracts: [
        "profit_margin",
        "business_goal",
        "human_budget_goal",
        "target_roas_or_cpa",
        "human_strategy_review"
      ],
      missing_read_contract_labels: [
        "marża albo model rentowności",
        "cel biznesowy",
        "cel budżetu od człowieka",
        "docelowy zwrot z reklam albo koszt pozyskania celu",
        "ocena strategii przez człowieka"
      ],
      blocked_claims: [
        "ocena opłacalności",
        "ocena wskaźników względem celu",
        "skalowanie budżetu",
        "zmiana budżetu",
        "zapis rekomendacji",
        "automatyczna optymalizacja"
      ],
      blocked_claim_labels: [
        "ocena opłacalności",
        "ocena wskaźników względem celu",
        "skalowanie budżetu",
        "zmiana budżetu",
        "zapis rekomendacji",
        "automatyczna optymalizacja"
      ],
      source_connectors: ["google_ads"],
      evidence_ids: ["ev_refresh_refresh_google_ads_test"],
      action_ids: ["act_record_ads_strategy_review"],
      apply_allowed: false,
      destructive: false,
      next_step:
        "Otwórz akcję strategii, sprawdź marżę, cel biznesowy, cel budżetu i target zwrotu z reklam/CPA, a potem zapisz outcome review."
    },
    allowed_metrics: [],
    missing_read_contracts: [
      "profit_margin",
      "business_goal",
      "human_budget_goal",
      "target_roas_or_cpa",
      "human_strategy_review"
    ],
    blocked_claims: [
      "opłacalność",
      "ocena marży",
      "skalowanie budżetu",
      "zmiana budżetu",
      "zapis rekomendacji",
      "zmarnowany budżet"
    ],
    source_connectors: ["google_ads"],
    evidence_ids: ["ev_refresh_refresh_google_ads_test"],
    metric_tiles: {
      marża: "brak",
      "cel biznesowy": "brak",
      "cel budżetu": "brak"
    },
    next_step:
      "Uzupełnij nie-sekretne wartości w repo-local .env: WILQ_ADS_PROFIT_MARGIN, WILQ_ADS_BUSINESS_GOAL, WILQ_ADS_BUDGET_GOAL oraz WILQ_ADS_TARGET_ROAS albo WILQ_ADS_TARGET_CPA_MICROS."
  },
  derived_kpi_read_contract: {
    id: "ads_derived_kpi_read_contract",
    status: "ready",
    title: "Google Ads: wyliczone KPI kampanii",
    summary:
      "WILQ może policzyć KPI dla 1 kampanii: CPA dostępne dla 1, zwrot z reklam dostępny dla 1. To są obliczenia z bieżących metryki, nie werdykt opłacalności.",
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
      "opłacalność",
      "skalowanie budżetu",
      "zmarnowany budżet",
      "zapis rekomendacji",
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
          "opłacalność",
          "skalowanie budżetu",
          "zmarnowany budżet",
          "zapis rekomendacji"
        ],
        blocked_claim_labels: [
          "opłacalność",
          "skalowanie budżetu",
          "zmarnowany budżet",
          "zapis rekomendacji"
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
      "skalowanie budżetu",
      "zmiana budżetu",
      "opłacalność",
      "zmarnowany budżet",
      "zapis rekomendacji"
    ],
    source_connectors: ["google_ads"],
    evidence_ids: ["ev_refresh_refresh_google_ads_test"],
    budget_rows: [
      {
        campaign_id: "123",
        campaign_name: "Ekologus Search",
        campaign_status: "ENABLED",
        campaign_status_label: "aktywna",
        advertising_channel_type: "SEARCH",
        advertising_channel_type_label: "sieć wyszukiwania",
        budget_id: "777",
        budget_name: "Ekologus Search budget",
        budget_period: "DAILY",
        budget_period_label: "dzienny",
        budget_status: "ENABLED",
        budget_status_label: "aktywna",
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
          operation_type_label: "zmiana budżetu kampanii",
          current_budget_amount_micros: 30000000,
          proposed_budget_amount_micros: 42000000,
          proposed_budget_delta_micros: 12000000,
          reason:
            "Podgląd budżetu z rekomendacji Google do sprawdzenia.",
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
          required_validation_labels: [
            "sprawdzenie aktywności kampanii",
            "sprawdzenie waluty konta",
            "tempo wydawania budżetu",
            "udział w wyświetleniach",
            "historia zmian",
            "cel budżetu od człowieka",
            "sprawdzenie zapisu budżetu w Google Ads",
            "potwierdzenie człowieka przed zapisem"
          ],
          blocked_claims: [
            "skalowanie budżetu",
            "zmiana budżetu",
            "wstrzymanie kampanii",
            "zmarnowany budżet",
            "opłacalność",
            "ocena kosztu pozyskania celu",
            "ocena zwrotu z reklam",
            "zapis rekomendacji"
          ],
          blocked_claim_labels: [
            "skalowanie budżetu",
            "zmiana budżetu",
            "wstrzymanie kampanii",
            "zmarnowany budżet",
            "opłacalność",
            "ocena kosztu pozyskania celu",
            "ocena zwrotu z reklam",
            "zapis rekomendacji"
          ],
          safety_review: {
            id: "budget_apply_preview_123_777_safety",
            budget_preview_id: "budget_apply_preview_123_777",
            safety_contract: "campaign_budget_apply_safety_v1",
            status: "blocked",
            reason:
              "Zapis zmiany budżetu zablokowany: proponowana zmiana przekracza limit 30%.",
            max_allowed_delta_percent: 0.3,
            current_budget_amount_micros: 30000000,
            proposed_budget_amount_micros: 42000000,
            proposed_delta_percent: 0.4,
            missing_requirements: [
              "change_history",
              "human_budget_goal",
              "mutation_audit",
              "human_confirm_before_apply",
              "budget_delta_within_30_percent"
            ],
            required_validation: [
              "review_campaign_activity",
              "verify_account_currency",
              "budget_pacing",
              "change_history",
              "human_budget_goal",
              "budget_delta_limit_30_percent",
              "campaign_budget_operation_preview",
              "mutation_audit",
              "human_confirm_before_apply"
            ],
            blocked_claims: [
              "zmiana budżetu",
              "skalowanie budżetu",
              "wstrzymanie kampanii",
              "opłacalność",
              "zmarnowany budżet",
              "automatic zapis zmian budżetu"
            ],
            evidence_ids: ["ev_refresh_refresh_google_ads_test"],
            api_mutation_ready: false,
            apply_allowed: false,
            destructive: false
          },
          api_mutation_ready: false,
          apply_allowed: false,
          destructive: false
        },
        missing_metrics: [],
        blocked_claims: [
          "skalowanie budżetu",
          "zmiana budżetu",
          "opłacalność",
          "zmarnowany budżet",
          "zapis rekomendacji"
        ]
      }
    ],
    shared_budget_distribution_rows: [
      {
        budget_id: "777",
        budget_name: "Ekologus Search budget",
        campaign_count: 2,
        budget_amount_micros: 30000000,
        seven_day_budget_micros: 210000000,
        total_cost_micros_7d: 164591174,
        spend_to_budget_ratio_7d: 0.781863,
        campaign_shares: [
          {
            campaign_id: "123",
            campaign_name: "Ekologus Search",
            campaign_status: "ENABLED",
            advertising_channel_type: "SEARCH",
            cost_micros_7d: 120000000,
            spend_share_7d: 0.729079,
            evidence_ids: ["ev_refresh_refresh_google_ads_test"]
          },
          {
            campaign_id: "124",
            campaign_name: "Ekologus Generic Search",
            campaign_status: "ENABLED",
            advertising_channel_type: "SEARCH",
            cost_micros_7d: 44591174,
            spend_share_7d: 0.270921,
            evidence_ids: ["ev_refresh_refresh_google_ads_test"]
          }
        ],
        evidence_ids: ["ev_refresh_refresh_google_ads_test"],
        blocked_claims: [
          "skalowanie budżetu",
          "zmiana budżetu",
          "wstrzymanie kampanii",
          "zmarnowany budżet",
          "opłacalność",
          "ocena kosztu pozyskania celu",
          "ocena zwrotu z reklam",
          "zapis rekomendacji"
        ],
        blocked_claim_labels: [
          "skalowanie budżetu",
          "zmiana budżetu",
          "wstrzymanie kampanii",
          "zmarnowany budżet",
          "opłacalność",
          "ocena kosztu pozyskania celu",
          "ocena zwrotu z reklam",
          "zapis rekomendacji"
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
        reason: "Podgląd budżetu z rekomendacji Google do sprawdzenia.",
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
          "skalowanie budżetu",
          "zmiana budżetu",
          "wstrzymanie kampanii",
          "zmarnowany budżet",
          "opłacalność",
          "ocena kosztu pozyskania celu",
          "ocena zwrotu z reklam",
          "zapis rekomendacji"
        ],
        safety_review: {
          id: "budget_apply_preview_123_777_safety",
          budget_preview_id: "budget_apply_preview_123_777",
          safety_contract: "campaign_budget_apply_safety_v1",
          status: "blocked",
          reason: "Zapis zmiany budżetu zablokowany: proponowana zmiana przekracza limit 30%.",
          max_allowed_delta_percent: 0.3,
          current_budget_amount_micros: 30000000,
          proposed_budget_amount_micros: 42000000,
          proposed_delta_percent: 0.4,
          missing_requirements: [
            "change_history",
            "human_budget_goal",
            "mutation_audit",
            "human_confirm_before_apply",
            "budget_delta_within_30_percent"
          ],
          required_validation: [
            "review_campaign_activity",
            "verify_account_currency",
            "budget_pacing",
            "change_history",
            "human_budget_goal",
            "budget_delta_limit_30_percent",
            "campaign_budget_operation_preview",
            "mutation_audit",
            "human_confirm_before_apply"
          ],
          blocked_claims: [
            "zmiana budżetu",
            "skalowanie budżetu",
            "wstrzymanie kampanii",
            "opłacalność",
            "zmarnowany budżet",
            "automatic zapis zmian budżetu"
          ],
          evidence_ids: ["ev_refresh_refresh_google_ads_test"],
          api_mutation_ready: false,
          apply_allowed: false,
          destructive: false
        },
        api_mutation_ready: false,
        apply_allowed: false,
        destructive: false
      }
    ],
    action_ids: ["act_prepare_ads_campaign_review_queue"],
    next_step:
      "Użyj tego jako kontekstu review; nie skaluj budżetu bez historii zmian i sprawdzonej akcji."
  },
  recommendations_read_contract: {
    id: "ads_recommendations_read_contract",
    status: "ready",
    title: "Google Ads: rekomendacje do review",
    summary:
      "WILQ ma 1 aktywną rekomendację Google Ads do sprawdzenia. Typy: CAMPAIGN_BUDGET. Podgląd wpływu dostępny dla 1; podgląd zmian dla 1.",
    allowed_metrics: [
      "recommendation_available",
      "recommendation_campaign_count",
      "recommendation_impact_base_clicks",
      "recommendation_impact_potential_clicks",
      "recommendation_impact_base_cost_micros",
      "recommendation_impact_potential_cost_micros"
    ],
    missing_read_contracts: ["change_history"],
    operator_review_gates: [
      "human_strategy_review",
      "review_recommendation_type",
      "review_impact_metrics",
      "review_change_history",
      "review_business_goal",
      "recommendation_apply_preview",
      "google_ads_rmf_compliance_review",
      "human_confirm_before_apply"
    ],
    blocked_claims: [
      "zapis rekomendacji",
      "automatyczne przyjęcie rekomendacji",
      "zmiana budżetu",
      "zapis zmian kampanii",
      "obietnica poprawy wyniku"
    ],
    source_connectors: ["google_ads"],
    evidence_ids: ["ev_refresh_refresh_google_ads_test"],
    recommendation_rows: [
      {
        recommendation_id: "rec-1",
        recommendation_resource_name: "customers/1234567890/recommendations/rec-1",
        recommendation_type: "CAMPAIGN_BUDGET",
        review_priority: "pilne",
        review_score: 70,
        review_reason:
          "Rekomendacja CAMPAIGN_BUDGET: podgląd wpływu: kliknięcia delta=+5, koszt delta=2.00, konwersje delta=brak. To jest kolejność przeglądu rekomendacji, nie zgoda na zapis zmian ani obietnica poprawy wyniku.",
        human_review_gates: [
          "sprawdź typ rekomendacji",
          "sprawdź metryki wpływu",
          "porównaj z historią zmian",
          "porównaj z celem biznesowym",
          "zweryfikuj RMF/compliance",
          "potwierdź człowiekiem przed zapisem"
        ],
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
          reason: "Podgląd zmian dla rekomendacji Google Ads jest do sprawdzenia w WILQ.",
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
            "zapis rekomendacji",
            "automatyczne przyjęcie rekomendacji",
            "zmiana budżetu",
            "zapis zmian kampanii",
            "obietnica poprawy wyniku"
          ],
          api_mutation_ready: false,
          apply_allowed: false,
          destructive: false
        },
        missing_metrics: [],
        blocked_claims: [
          "zapis rekomendacji",
          "automatyczne przyjęcie rekomendacji",
          "zmiana budżetu",
          "zapis zmian kampanii"
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
        reason: "Podgląd zmian dla rekomendacji Google Ads jest do sprawdzenia w WILQ.",
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
          "zapis rekomendacji",
          "automatyczne przyjęcie rekomendacji",
          "zmiana budżetu",
          "zapis zmian kampanii",
          "obietnica poprawy wyniku"
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
      "skalowanie budżetu",
      "zmiana budżetu",
      "zmarnowany budżet",
      "obietnica poprawy wyniku",
      "zapis zmian kampanii"
    ],
    source_connectors: ["google_ads"],
    evidence_ids: ["ev_refresh_refresh_google_ads_test"],
    impression_share_rows: [
      {
        campaign_id: "123",
        campaign_name: "Ekologus Search",
        campaign_status: "ENABLED",
        campaign_status_label: "aktywna",
        advertising_channel_type: "SEARCH",
        advertising_channel_type_label: "sieć wyszukiwania",
        search_impression_share: 0.73,
        search_budget_lost_impression_share: 0.18,
        search_rank_lost_impression_share: 0.09,
        evidence_ids: ["ev_refresh_refresh_google_ads_test"],
        metric_facts: [],
        missing_metrics: [],
        blocked_claims: [
          "skalowanie budżetu",
          "zmiana budżetu",
          "zmarnowany budżet",
          "obietnica poprawy wyniku"
        ]
      }
    ],
    next_step:
      "Użyj udziału w wyświetleniach jako kontekstu review, nie jako decyzji budżetowej."
  },
  campaign_triage_read_contract: {
    id: "ads_campaign_triage_read_contract",
    status: "ready",
    title: "Kolejność oceny kampanii Ads",
    summary:
      "WILQ połączył campaign activity, KPI, budżet, rekomendacje i impression share dla 1 kampanii. To nie jest werdykt zmarnowany budżet, opłacalność, CPA ani zwrot z reklam.",
    allowed_metrics: [
      "clicks",
      "impressions",
      "cost_micros",
      "conversions",
      "conversion_value",
      "ctr",
      "average_cpc_micros",
      "conversion_rate",
      "cost_per_conversion_micros",
      "roas",
      "spend_to_budget_ratio_7d",
      "search_budget_lost_impression_share",
      "recommendation_count"
    ],
    missing_read_contracts: ["target_roas_or_cpa", "human_strategy_review"],
    blocked_claims: [
      "zmarnowany budżet",
      "opłacalność",
      "skalowanie budżetu",
      "zmiana budżetu",
      "zapis rekomendacji",
      "zapis zmian kampanii"
    ],
    source_connectors: ["google_ads"],
    evidence_ids: ["ev_refresh_refresh_google_ads_test"],
    triage_rows: [
      {
        campaign_id: "123",
        campaign_name: "Ekologus Search",
        campaign_status: "ENABLED",
        advertising_channel_type: "SEARCH",
        review_priority: "pilne",
        review_score: 90,
        review_reason:
          "Kolejność oceny kampanii wynika z kosztu, kliknięć, konwersji, budżetu, rekomendacji i impression share.",
        next_step:
          "Sprawdź cel kampanii, jakość konwersji, budżet, listy wyszukiwanych haseł i rekomendacje bez zapisu zmian.",
        target_status: "no_target",
        target_status_label: "brak celu",
        clicks: 107,
        impressions: 2783,
        cost_micros: 164591174,
        conversions: 2.5,
        conversion_value: 450.75,
        ctr: 0.038448,
        average_cpc_micros: 1538235.271028,
        conversion_rate: 0.023364,
        cost_per_conversion_micros: 65836469.6,
        roas: 2.738589,
        spend_to_budget_ratio_7d: 0.783768,
        search_budget_lost_impression_share: 0.18,
        recommendation_count: 1,
        recommendation_types: ["CAMPAIGN_BUDGET"],
        has_budget_apply_preview: true,
        has_recommendation_apply_preview: true,
        evidence_ids: ["ev_refresh_refresh_google_ads_test"],
        action_ids: ["act_prepare_ads_campaign_review_queue"],
        source_metric_names: [
          "clicks",
          "conversion_value",
          "conversions",
          "cost_micros",
          "impressions",
          "budget_amount_micros",
          "recommendation_available",
          "search_budget_lost_impression_share"
        ],
        missing_read_contracts: ["target_roas_or_cpa", "human_strategy_review"],
        missing_read_contract_labels: [
          "docelowy zwrot z reklam albo koszt pozyskania celu",
          "ocena strategii przez człowieka"
        ],
        blocked_claims: [
          "zmarnowany budżet",
          "opłacalność",
          "skalowanie budżetu",
          "zmiana budżetu",
          "zapis rekomendacji",
          "zapis zmian kampanii"
        ],
        blocked_claim_labels: [
          "zmarnowany budżet",
          "opłacalność",
          "skalowanie budżetu",
          "zmiana budżetu",
          "zapis rekomendacji",
          "zapis zmian kampanii"
        ],
        human_review_gates: [
          "review_campaign_goal",
          "review_conversion_quality",
          "review_budget_context",
          "review_search_terms_before_budget_decision",
          "human_strategy_review"
        ]
      }
    ],
    action_ids: ["act_prepare_ads_campaign_review_queue"],
    next_step:
      "Przejrzyj kampanie od góry kolejki. Apply i skalowanie zostają zablokowane."
  },
  optimizer_readiness_contract: {
    id: "ads_optimizer_readiness_contract",
    status: "review_ready",
    status_label: "gotowe do oceny",
    mode: "review_only",
    mode_label: "ocena bez zapisu",
    title: "Ads Optimizer readiness",
    summary:
      "WILQ może przygotować sprawdzenie kampanii i listy wyszukiwanych haseł, ale zapis zmian oraz ocena wpływu zmian są zablokowane do czasu pełnych kontraktów audytu.",
    ready_area_count: 3,
    blocked_area_count: 2,
    readiness_items: [
      {
        id: "campaign_review_queue",
        label: "kampanie do oceny",
        title: "Kolejność oceny kampanii",
        status: "ready",
        status_label: "gotowe",
        summary:
          "Campaign activity, KPI, budżet, rekomendacje i impression share są dostępne jako kolejka oceny.",
        next_step:
          "Przejrzyj kampanie od góry kolejki bez zapisu zmian i bez werdyktu zmarnowany budżet.",
        source_contract_ids: ["ads_campaign_triage_read_contract"],
        allowed_metrics: ["clicks", "impressions", "cost_micros", "conversions"],
        missing_read_contracts: [],
        missing_read_contract_labels: [],
        operator_review_gates: ["human_strategy_review"],
        blocked_claims: ["zmarnowany budżet", "opłacalność", "zapis zmian kampanii"],
        blocked_claim_labels: ["zmarnowany budżet", "opłacalność", "zapis zmian kampanii"],
        source_connectors: ["google_ads"],
        evidence_ids: ["ev_refresh_refresh_google_ads_test"],
        action_ids: ["act_prepare_ads_campaign_review_queue"],
        risk: "medium",
        risk_label: "średnie"
      },
      {
        id: "search_terms_review_queue",
        label: "wyszukiwane hasła",
        title: "Search terms do review",
        status: "ready",
        status_label: "gotowe",
        summary:
          "Search-term evidence jest gotowe do ręcznego review, bez automatycznych wykluczeń.",
        next_step:
          "Użyj listy wyszukiwanych haseł jako listy review, nie jako gotowej listy wykluczeń.",
        source_contract_ids: ["ads_search_term_review_summary_contract"],
        allowed_metrics: ["search_term", "clicks", "impressions", "cost_micros"],
        missing_read_contracts: ["human_confirm_before_apply"],
        missing_read_contract_labels: ["potwierdzenie człowieka przed zapisem"],
        operator_review_gates: ["review_search_term_context"],
        blocked_claims: ["dodanie wykluczających słów kluczowych", "marnowanie budżetu na zapytaniach"],
        blocked_claim_labels: ["dodanie wykluczających słów kluczowych", "marnowanie budżetu na zapytaniach"],
        source_connectors: ["google_ads"],
        evidence_ids: ["ev_refresh_refresh_google_ads_test"],
        action_ids: ["act_prepare_negative_keyword_review_queue"],
        risk: "medium",
        risk_label: "średnie"
      },
      {
        id: "custom_segments_review_queue",
        label: "segmenty niestandardowe",
        title: "Segmenty niestandardowe do sprawdzenia",
        status: "ready",
        status_label: "gotowe",
        summary:
          "Segmenty niestandardowe mogą być przygotowane do sprawdzenia z wyszukiwanych haseł i dowodów Keyword Planner.",
        next_step:
          "Przejrzyj wyszukiwane hasła i wzbogacenie danych przed jakimkolwiek kierowaniem reklam.",
        source_contract_ids: ["ads_custom_segments_read_contract"],
        allowed_metrics: ["source_terms", "avg_monthly_searches"],
        missing_read_contracts: ["forecast_or_audience_size"],
        missing_read_contract_labels: ["prognoza albo rozmiar odbiorców"],
        operator_review_gates: ["human_confirm_before_apply"],
        blocked_claims: ["rozmiar odbiorców", "zapis kierowania reklam"],
        blocked_claim_labels: ["rozmiar odbiorców", "zapis kierowania reklam"],
        source_connectors: ["google_ads"],
        evidence_ids: ["ev_refresh_refresh_google_ads_test"],
        action_ids: ["act_prepare_custom_segments_from_search_terms"],
        risk: "medium",
        risk_label: "średnie"
      },
      {
        id: "change_history_impact_review",
        label: "historia zmian",
        title: "Impact review historii zmian",
        status: "blocked",
        status_label: "zablokowane",
        summary:
          "Change events są dostępne, ale WILQ nie ma jeszcze pre/post performance windows ani review wpływu zmian.",
        next_step:
          "Zostaw impact review zablokowany do czasu kontraktu pre/post performance.",
        source_contract_ids: [
          "ads_change_history_read_contract",
          "ads_change_impact_readiness_contract"
        ],
        allowed_metrics: ["change_event_available", "change_event_changed_field_count"],
        missing_read_contracts: [
          "pre_change_performance_window",
          "post_change_performance_window",
          "human_change_impact_review"
        ],
        missing_read_contract_labels: [
          "okno wyników przed zmianą",
          "okno wyników po zmianie",
          "ręczna ocena wpływu zmian"
        ],
        operator_review_gates: ["human_change_impact_review"],
        blocked_claims: ["wpływ zmian", "obietnica poprawy wyniku", "zapis zmian kampanii"],
        blocked_claim_labels: ["wpływ zmian", "obietnica poprawy wyniku", "zapis zmian kampanii"],
        source_connectors: ["google_ads"],
        evidence_ids: ["ev_refresh_refresh_google_ads_test"],
        action_ids: [],
        risk: "high",
        risk_label: "wysokie"
      },
      {
        id: "ads_apply_safety_gate",
        label: "bramka zapisu zmian",
        title: "Apply i mutacje Ads",
        status: "blocked",
        status_label: "zablokowane",
        summary:
          "Każda mutacja Ads wymaga osobnej akcji, preview, confirm i audytu.",
        next_step:
          "Nie wykonuj apply z poziomu diagnostyki. Najpierw sprawdź w WILQ osobną akcję.",
        source_contract_ids: ["ads_action_safety_contract"],
        allowed_metrics: [],
        missing_read_contracts: ["google_ads_mutation_audit", "human_confirm_before_apply"],
        missing_read_contract_labels: [
          "sprawdzenie zapisu zmian w Google Ads",
          "potwierdzenie człowieka przed zapisem"
        ],
        operator_review_gates: ["human_confirm_before_apply"],
        blocked_claims: ["zmiana budżetu", "zapis rekomendacji", "zapis zmian kampanii"],
        blocked_claim_labels: ["zmiana budżetu", "zapis rekomendacji", "zapis zmian kampanii"],
        source_connectors: ["google_ads"],
        evidence_ids: ["ev_refresh_refresh_google_ads_test"],
        action_ids: [],
        risk: "critical",
        risk_label: "krytyczne"
      }
    ],
    allowed_metrics: [
      "clicks",
      "impressions",
      "cost_micros",
      "conversions",
      "search_term",
      "change_event_available"
    ],
    missing_read_contracts: [
      "pre_change_performance_window",
      "post_change_performance_window",
      "human_change_impact_review",
      "google_ads_mutation_audit",
      "human_confirm_before_apply"
    ],
    missing_read_contract_labels: [
      "okno wyników przed zmianą",
      "okno wyników po zmianie",
      "ręczna ocena wpływu zmian",
      "sprawdzenie zapisu zmian w Google Ads",
      "potwierdzenie człowieka przed zapisem"
    ],
    operator_review_gates: ["human_strategy_review", "human_confirm_before_apply"],
    blocked_claims: [
      "zmarnowany budżet",
      "ocena kosztu pozyskania celu",
      "ocena zwrotu z reklam",
      "wpływ zmian",
      "obietnica poprawy wyniku",
      "zapis zmian kampanii"
    ],
    blocked_claim_labels: [
      "zmarnowany budżet",
      "ocena kosztu pozyskania celu",
      "ocena zwrotu z reklam",
      "wpływ zmian",
      "obietnica poprawy wyniku",
      "zapis zmian kampanii"
    ],
    source_connectors: ["google_ads"],
    evidence_ids: ["ev_refresh_refresh_google_ads_test"],
    action_ids: [
      "act_prepare_ads_campaign_review_queue",
      "act_prepare_negative_keyword_review_queue",
      "act_prepare_custom_segments_from_search_terms"
    ],
    api_mutation_ready: false,
    apply_allowed: false,
    next_step:
      "Pracuj tylko na obszarach ready do review; impact i apply zostają zablokowane."
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
      "wpływ zmian",
      "obietnica poprawy wyniku",
      "skalowanie budżetu",
      "zmiana budżetu",
      "zapis zmian kampanii"
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
          "wpływ zmian",
          "obietnica poprawy wyniku",
          "zmiana budżetu",
          "zapis zmian kampanii"
        ]
      }
    ],
    next_step:
      "Użyj historii zmian jako kontekstu audytu, nie jako dowodu wpływu zmiany."
  },
  change_impact_readiness_contract: {
    id: "ads_change_impact_readiness_contract",
    status: "blocked",
    title: "Google Ads: gotowość impact review zmian",
    summary:
      "WILQ ma 1 zdarzeń zmian do impact review i 1 powiązanych snapshotów kampanii. To jest readiness do ręcznego audytu, nie dowód wpływu zmian.",
    allowed_metrics: [
      "change_event_available",
      "change_event_changed_field_count",
      "current_campaign_clicks",
      "current_campaign_impressions",
      "current_campaign_cost_micros",
      "current_campaign_conversions",
      "current_campaign_conversion_value"
    ],
    missing_read_contracts: [
      "pre_change_performance_window",
      "post_change_performance_window",
      "human_change_impact_review",
      "apply_preview"
    ],
    blocked_claims: [
      "wpływ zmian",
      "obietnica poprawy wyniku",
      "skalowanie budżetu",
      "zmiana budżetu",
      "zapis zmian kampanii"
    ],
    source_connectors: ["google_ads"],
    evidence_ids: ["ev_refresh_refresh_google_ads_test"],
    readiness_rows: [
      {
        change_event_id: "change-1",
        campaign_id: "123",
        campaign_name: "Ekologus Search",
        change_date_time: "2026-06-18 12:30:00.000000",
        changed_fields: ["campaign.status", "campaign_budget.amount_micros"],
        current_campaign_metrics_available: true,
        pre_window_available: false,
        post_window_available: false,
        current_clicks: 107,
        current_impressions: 2783,
        current_cost_micros: 164591174,
        current_conversions: 2.5,
        current_conversion_value: 450.75,
        missing_read_contracts: [
          "pre_change_performance_window",
          "post_change_performance_window",
          "human_change_impact_review",
          "apply_preview"
        ],
        evidence_ids: ["ev_refresh_refresh_google_ads_test"],
        blocked_claims: [
          "wpływ zmian",
          "obietnica poprawy wyniku",
          "skalowanie budżetu",
          "zmiana budżetu",
          "zapis zmian kampanii"
        ]
      }
    ],
    action_ids: ["act_review_ads_change_history_impact"],
    api_mutation_ready: false,
    apply_allowed: false,
    next_step:
      "Użyj tego jako checklisty gotowości: najpierw dołóż okna pomiaru przed/po i ręczne sprawdzenie wpływu zmian, potem dopiero rozważ zapis zmian."
  },
  search_terms_read_contract: {
    id: "ads_search_terms_read_contract",
    status: "ready",
    title: "Google Ads: zapytania użytkowników",
    summary:
      "WILQ ma 1 wierszy zapytań: kliknięcia=12, wyświetlenia=140, koszt=9,00 zł, konwersje=1, wartość konwersji=120.",
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
    missing_read_contracts: ["90_day_safety_check"],
    operator_review_gates: ["negative_keyword_action_validation"],
    blocked_claims: [
      "marnowanie budżetu na zapytaniach",
      "propozycje wykluczeń",
      "dodanie wykluczających słów kluczowych",
      "koszt pozyskania celu",
      "zwrot z reklam"
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
        blocked_claims: ["koszt pozyskania celu", "zwrot z reklam", "dodanie wykluczających słów kluczowych", "zmarnowany budżet"]
      }
    ],
    next_step: "Użyj wierszy zapytań jako przeglądu danych z reklam."
  },
  search_term_review_summary_contract: {
    id: "ads_search_term_review_summary_contract",
    status: "ready",
    title: "Google Ads: kolejność review zapytań",
    summary:
      "WILQ ma 1 wierszy wyszukiwanych haseł do ręcznej oceny: kliknięcia=12, wyświetlenia=140, koszt=9,00 zł, konwersje=1, wiersze bez konwersji=0.",
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
    missing_read_contracts: ["90_day_safety_check"],
    operator_review_gates: [
      "human_intent_review",
      "negative_keyword_action_validation"
    ],
    blocked_claims: ["marnowanie budżetu na zapytaniach", "dodanie wykluczających słów kluczowych", "koszt pozyskania celu", "zwrot z reklam"],
    source_connectors: ["google_ads"],
    evidence_ids: ["ev_refresh_refresh_google_ads_test"],
    total_search_term_count: 1,
    zero_conversion_search_term_count: 0,
    total_clicks: 12,
    total_impressions: 140,
    total_cost_micros: 9000000,
    total_conversions: 1,
    top_cost_search_terms: [
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
        evidence_ids: ["ev_refresh_refresh_google_ads_test"],
        blocked_claims: ["marnowanie budżetu na zapytaniach", "dodanie wykluczających słów kluczowych", "koszt pozyskania celu", "zwrot z reklam"]
      }
    ],
    campaign_review_rows: [
      {
        campaign_id: "123",
        campaign_name: "Ekologus Search",
        search_term_count: 1,
        zero_conversion_search_term_count: 0,
        clicks: 12,
        impressions: 140,
        cost_micros: 9000000,
        conversions: 1,
        evidence_ids: ["ev_refresh_refresh_google_ads_test"],
        blocked_claims: ["marnowanie budżetu na zapytaniach", "dodanie wykluczających słów kluczowych", "koszt pozyskania celu", "zwrot z reklam"]
      }
    ],
    next_step:
      "Najpierw przejrzyj kampanie i zapytania z największym kosztem."
  },
  search_term_ngram_read_contract: {
    id: "ads_search_term_ngram_read_contract",
    status: "ready",
    title: "Google Ads: n-gramy zapytań",
    summary:
      "WILQ zgrupował 1 n-gramów z 1 wystąpień listy wyszukiwanych haseł: kliknięcia=12, koszt=9,00 zł.",
    allowed_metrics: [
      "ngram",
      "ngram_size",
      "source_search_term_count",
      "sample_search_terms",
      "clicks",
      "impressions",
      "cost_micros",
      "conversions",
      "conversion_value"
    ],
    missing_read_contracts: [
      "human_intent_review",
      "negative_keyword_change_preview"
    ],
    operator_review_gates: [
      "human_intent_review",
      "negative_keyword_action_validation"
    ],
    blocked_claims: [
      "marnowanie budżetu na zapytaniach",
      "propozycje wykluczeń",
      "dodanie wykluczających słów kluczowych",
      "koszt pozyskania celu",
      "zwrot z reklam",
      "utrata konwersji"
    ],
    source_connectors: ["google_ads"],
    evidence_ids: ["ev_refresh_refresh_google_ads_test"],
    ngram_rows: [
      {
        ngram: "bdo rejestracja",
        ngram_size: 2,
        source_search_term_count: 1,
        sample_search_terms: ["bdo rejestracja"],
        clicks: 12,
        impressions: 140,
        cost_micros: 9000000,
        conversions: 1,
        conversion_value: 120,
        evidence_ids: ["ev_refresh_refresh_google_ads_test"],
        metric_facts: [],
        missing_metrics: [],
        blocked_claims: ["koszt pozyskania celu", "zwrot z reklam", "dodanie wykluczających słów kluczowych", "marnowanie budżetu na zapytaniach"]
      }
    ],
    next_step:
      "Użyj n-gramów do znalezienia powtarzających się tematów w zapytaniach."
  },
  search_term_safety_read_contract: {
    id: "ads_search_term_safety_read_contract",
    status: "ready",
    title: "Google Ads: 90-dniowy safety read zapytań",
    summary:
      "WILQ ma 90-dniowy odczyt bezpieczeństwa dla 1 zapytań: kliknięcia=10, wyświetlenia=120, koszt=8,00 zł, konwersje=0, wartość konwersji=0.",
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
      "keyword match context"
    ],
    operator_review_gates: ["human_intent_review"],
    blocked_claims: [
      "dodanie wykluczających słów kluczowych",
      "marnowanie budżetu na zapytaniach",
      "utrata konwersji",
      "koszt pozyskania celu",
      "zwrot z reklam"
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
        blocked_claims: ["koszt pozyskania celu", "zwrot z reklam", "dodanie wykluczających słów kluczowych", "zmarnowany budżet"]
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
      "WILQ ma kontekst 1 istniejących keywordów z match types: BROAD.",
    allowed_metrics: [
      "keyword_text",
      "keyword_match_type",
      "criterion_status",
      "keyword_negative",
      "campaign",
      "ad_group"
    ],
    missing_read_contracts: [],
    operator_review_gates: ["human_intent_review"],
    blocked_claims: [
      "dodanie wykluczających słów kluczowych",
      "marnowanie budżetu na zapytaniach",
      "utrata konwersji",
      "koszt pozyskania celu",
      "zwrot z reklam"
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
        blocked_claims: ["dodanie wykluczających słów kluczowych", "marnowanie budżetu na zapytaniach", "zmarnowany budżet"]
      }
    ],
    next_step: "Użyj tego jako kontekstu review, nie jako zgody na apply."
  },
  keyword_planner_read_contract: {
    id: "ads_keyword_planner_read_contract",
    status: "ready",
    title: "Keyword Planner: wzbogacenie segmentów",
    summary:
      "WILQ ma 1 pomysł Keyword Planner dla wyszukiwanych haseł z Ads. Najwyższe avg_monthly_searches=100.",
    allowed_metrics: [
      "keyword_idea_text",
      "keyword_planner_avg_monthly_searches",
      "keyword_planner_competition_index",
      "keyword_planner_low_top_of_page_bid_micros",
      "keyword_planner_high_top_of_page_bid_micros"
    ],
    missing_read_contracts: ["forecast_or_audience_size"],
    operator_review_gates: [
      "review_keyword_planner_ideas",
      "reject_off-topic_or_brand_terms",
      "human_confirm_before_apply"
    ],
    blocked_claims: [
      "rozmiar odbiorców",
      "prognoza",
      "wzrost konwersji",
      "zwrot z reklam",
      "zapis kierowania reklam",
      "skuteczność kampanii"
    ],
    source_connectors: ["google_ads"],
    evidence_ids: ["ev_refresh_refresh_google_ads_test"],
    idea_rows: [
      {
        idea_text: "bdo szkolenie",
        avg_monthly_searches: 100,
        competition: "MEDIUM",
        competition_index: 55,
        low_top_of_page_bid_micros: 1200000,
        high_top_of_page_bid_micros: 4400000,
        source_terms: ["bdo rejestracja"],
        evidence_ids: ["ev_refresh_refresh_google_ads_test"],
        metric_facts: [],
        missing_metrics: [],
        blocked_claims: [
          "rozmiar odbiorców",
          "prognoza",
          "wzrost konwersji",
          "zwrot z reklam",
          "zapis kierowania reklam"
        ]
      }
    ],
    next_step:
      "Użyj wzbogacenia jako dodatkowego kontekstu przy segmentach. Nie traktuj go jako prognozy."
  },
  custom_segments_read_contract: {
    id: "ads_custom_segments_read_contract",
    status: "ready",
    title: "Segmenty z realnych wyszukiwanych haseł",
    summary: "WILQ ma 1 propozycję segmentu, 1 wyszukiwane hasło z dowodów Google Ads oraz 1 pomysł Keyword Planner.",
    candidates: [
      {
        id: "ads_custom_segment_123",
        name: "Zapytania użytkowników: Ekologus Search",
        intent: "zainteresowanie z wyszukiwanych haseł",
        review_priority: "wysokie",
        review_score: 65,
        review_reason:
          "Wyszukiwane hasła=1, kliknięcia=12, wyświetlenia=140, koszt=9.00, konwersje=1, odrzucone terminy=0. To jest kolejność oceny segmentu, nie dowód rozmiaru odbiorców, kierowania reklam ani wpływu na kampanię.",
        human_review_gates: [
          "sprawdź intencję wyszukiwanych haseł",
          "odrzuć brand, konkurencję i frazy o niskiej intencji",
          "sprawdź Keyword Planner enrichment",
          "sprawdź prognozę albo rozmiar odbiorców",
          "zatwierdź segment przed zapisem"
        ],
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
            blocked_claims: ["koszt pozyskania celu", "zwrot z reklam", "dodanie wykluczających słów kluczowych", "zmarnowany budżet"]
          }
        ],
        keyword_planner_ideas: [
          {
            idea_text: "bdo szkolenie",
            avg_monthly_searches: 100,
            competition: "MEDIUM",
            competition_index: 55,
            low_top_of_page_bid_micros: 1200000,
            high_top_of_page_bid_micros: 4400000,
            source_terms: ["bdo rejestracja"],
            evidence_ids: ["ev_refresh_refresh_google_ads_test"],
            metric_facts: [],
            missing_metrics: [],
            blocked_claims: [
              "rozmiar odbiorców",
              "prognoza",
              "wzrost konwersji",
              "zwrot z reklam",
              "zapis kierowania reklam"
            ]
          }
        ],
        source_connectors: ["google_ads"],
        evidence_ids: ["ev_refresh_refresh_google_ads_test"],
        metric_facts: [],
        confidence: "medium",
        validation_status: "pending_validation",
        payload_preview: {
          id: "preview_ads_custom_segment_123",
          custom_segment_name: "Zapytania użytkowników: Ekologus Search",
          member_type: "KEYWORD",
          source_terms: ["bdo rejestracja"],
          campaign_id: "123",
          campaign_name: "Ekologus Search",
          reason: "Podgląd segmentu odbiorców oparty na wyszukiwanych hasłach do sprawdzenia.",
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
            "rozmiar odbiorców",
            "wzrost konwersji",
            "zwrot z reklam",
            "zapis kierowania reklam",
            "skuteczność kampanii"
          ],
          targeting_preview: [
            {
              id: "targeting_preview_ads_custom_segment_123",
              custom_segment_preview_id: "preview_ads_custom_segment_123",
              target_scope: "campaign_context_review",
              campaign_id: "123",
              campaign_name: "Ekologus Search",
              operation_type: "custom_segment_targeting_review",
              reason: "Podgląd kontekstu kierowania reklam; zapis zmian pozostaje zablokowany.",
              required_validation: [
                "keyword_planner_enrichment",
                "forecast_or_audience_size",
                "human_confirm_before_apply",
                "mutation_audit_required"
              ],
              blocked_claims: [
                "rozmiar odbiorców",
                "wzrost konwersji",
                "zwrot z reklam",
                "zapis kierowania reklam",
                "skuteczność kampanii"
              ],
              api_mutation_ready: false,
              apply_allowed: false,
              destructive: false
            }
          ],
          safety_review: customSegmentSafetyReview("preview_ads_custom_segment_123"),
          api_mutation_ready: false,
          apply_allowed: false,
          destructive: false
        },
        blocked_claims: [
          "rozmiar odbiorców",
          "wzrost konwersji",
          "zwrot z reklam",
          "zapis kierowania reklam",
          "skuteczność kampanii"
        ],
        next_step: "Użyj tych terminów jako propozycji bez zapisu zmian."
      }
    ],
    payload_preview: [
      {
        id: "preview_ads_custom_segment_123",
        custom_segment_name: "Zapytania użytkowników: Ekologus Search",
        member_type: "KEYWORD",
        source_terms: ["bdo rejestracja"],
        campaign_id: "123",
        campaign_name: "Ekologus Search",
        reason: "Podgląd segmentu odbiorców oparty na wyszukiwanych hasłach do sprawdzenia.",
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
          "rozmiar odbiorców",
          "wzrost konwersji",
          "zwrot z reklam",
          "zapis kierowania reklam",
          "skuteczność kampanii"
        ],
        safety_review: customSegmentSafetyReview("preview_ads_custom_segment_123"),
        api_mutation_ready: false,
        apply_allowed: false,
        destructive: false
      }
    ],
    audience_forecast_read_contract: {
      id: "ads_custom_segment_audience_forecast_read_contract",
      status: "blocked",
      title: "Prognoza i rozmiar odbiorców segmentów",
      summary:
        "WILQ sprawdził 1 propozycję segmentu, ale nie ma dowodów prognozy ani rozmiaru odbiorców.",
      checked_candidate_count: 1,
      forecast_row_count: 1,
      forecast_rows: [
        {
          id: "forecast_ads_custom_segment_123",
          candidate_id: "ads_custom_segment_123",
          custom_segment_name: "Zapytania użytkowników: Ekologus Search",
          status: "missing_forecast",
          forecast_available: false,
          audience_size: null,
          source_terms: ["bdo rejestracja"],
          reason:
            "Brak dowodów WILQ dla prognozy albo rozmiaru odbiorców tego segmentu.",
          evidence_ids: ["ev_refresh_refresh_google_ads_test"],
          blocked_claims: [
            "rozmiar odbiorców",
            "wzrost konwersji",
            "zwrot z reklam",
            "zapis kierowania reklam",
            "skuteczność kampanii"
          ]
        }
      ],
      missing_read_contracts: ["forecast_or_audience_size"],
      operator_review_gates: ["forecast_or_audience_size", "human_confirm_before_apply"],
      blocked_claims: [
        "rozmiar odbiorców",
        "wzrost konwersji",
        "zwrot z reklam",
        "zapis kierowania reklam",
        "skuteczność kampanii"
      ],
      source_connectors: ["google_ads"],
      evidence_ids: ["ev_refresh_refresh_google_ads_test"],
      next_step: "Nie oceniaj zasięgu ani skuteczności segmentu bez forecastu."
    },
    source_connectors: ["google_ads"],
    evidence_ids: ["ev_refresh_refresh_google_ads_test"],
    missing_read_contracts: ["forecast_or_audience_size"],
    operator_review_gates: [
      "review_source_terms",
      "reject_brand_or_low_intent_terms",
      "keyword_planner_enrichment",
      "forecast_or_audience_size",
      "human_confirm_before_apply"
    ],
    blocked_claims: [
      "rozmiar odbiorców",
      "wzrost konwersji",
      "zwrot z reklam",
      "zapis kierowania reklam",
      "skuteczność kampanii"
    ],
    action_ids: ["act_prepare_custom_segments_from_search_terms"],
    next_step: "Przejrzyj wyszukiwane hasła i sprawdź propozycję w WILQ przed zapisem zmian."
  },
  negative_keywords_read_contract: {
    id: "ads_negative_keywords_read_contract",
    status: "ready",
    title: "Review wykluczeń z listy wyszukiwanych haseł",
    summary:
      "WILQ ma 1 terminów do review: mają koszt lub kliknięcia i zero konwersji w bieżącym Google Ads evidence.",
    candidates: [
      {
        id: "ads_negative_keyword_review_123_789_odpady_cena",
        search_term: "odpady cena",
        review_priority: "wysokie",
        review_score: 53,
        review_reason:
          "Bieżący read: kliknięcia=6, koszt=5.00, konwersje=0; 90 dni: kliknięcia=10, koszt=8.00, konwersje=0; kontekst keywords=1 rows. To jest kolejność review, nie ocena zmarnowanego budżetu.",
        human_review_gates: [
          "sprawdź intencję zapytania",
          "porównaj z istniejącymi keywords i match types",
          "sprawdź 90-dniowy safety read",
          "zatwierdź poziom wykluczenia przed zapisem"
        ],
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
            blocked_claims: ["dodanie wykluczających słów kluczowych", "marnowanie budżetu na zapytaniach", "zmarnowany budżet"]
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
          blocked_claims: ["dodanie wykluczających słów kluczowych", "marnowanie budżetu na zapytaniach"],
          api_mutation_ready: false,
          apply_allowed: false,
          destructive: false
        },
        required_checks: [
          "review_search_term_context",
          "check_existing_keywords_and_match_types",
          "90_day_safety_check",
          "negative_keyword_change_preview",
          "human_confirm_before_apply"
        ],
        safety_status: "read_ready_needs_human_review",
        validation_status: "pending_validation",
        blocked_claims: ["dodanie wykluczających słów kluczowych", "marnowanie budżetu na zapytaniach", "koszt pozyskania celu", "zwrot z reklam"],
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
        blocked_claims: ["dodanie wykluczających słów kluczowych", "marnowanie budżetu na zapytaniach"],
        api_mutation_ready: false,
        apply_allowed: false,
        destructive: false
      }
    ],
    source_connectors: ["google_ads"],
    evidence_ids: ["ev_refresh_refresh_google_ads_test"],
    missing_read_contracts: [],
    blocked_claims: [
      "dodanie wykluczających słów kluczowych",
      "marnowanie budżetu na zapytaniach",
      "utrata konwersji",
      "koszt pozyskania celu",
      "zwrot z reklam"
    ],
    action_ids: ["act_prepare_negative_keyword_review_queue"],
    next_step: "Przejrzyj propozycje jako akcje do sprawdzenia i sprawdź podgląd zmian."
  },
  operator_summary: {
    id: "ads_operator_summary",
    title: "Co marketer ma sprawdzić teraz w Google Ads",
    summary:
      "WILQ pokazuje tylko decyzje wynikające z odczytu Google Ads. Kampanie, zapytania, KPI i rekomendacje można przeglądać jako ocenę opartą na dowodach.",
    next_step:
      "Przejrzyj top decyzje w tej kolejności. Nie zapisuj wykluczeń, budżetów ani rekomendacji bez podglądu zmian i sprawdzenia w WILQ.",
    top_decision_ids: [
      "ads_review_campaign_activity",
      "ads_review_campaign_triage",
      "ads_review_derived_kpis",
      "ads_review_recommendations",
      "ads_review_search_terms"
    ],
    campaign_count: 1,
    search_term_count: 1,
    total_clicks: 107,
    total_impressions: 2783,
    total_cost_micros: 164591174,
    total_conversions: 2.5,
    total_conversion_value: 450.75,
    ready_area_count: 5,
    blocked_area_count: 3,
    allowed_metrics: ["clicks", "impressions", "cost_micros", "conversions"],
    missing_read_contracts: ["profit_margin", "human_strategy_review"],
    operator_review_gates: ["human_strategy_review", "review_campaign_goal"],
    source_connectors: ["google_ads"],
    evidence_ids: ["ev_refresh_refresh_google_ads_test"],
    action_ids: ["act_prepare_ads_campaign_review_queue"],
    blocked_claims: ["zwrot z reklam", "zmiana budżetu", "dodanie wykluczających słów kluczowych"],
    missing_read_contract_labels: ["marża albo cel opłacalności", "ocena strategii przez człowieka"],
    blocked_claim_labels: ["zwrot z reklam", "zmiana budżetu", "dodanie wykluczających słów kluczowych"]
  },
  decision_queue: [
    {
      id: "ads_review_campaign_activity",
      decision_type: "review_campaign_activity",
      status: "ready",
      title: "Przejrzyj aktywność kampanii Google Ads",
      summary:
        "WILQ ma 1 wierszy kampanii: kliknięcia=107, wyświetlenia=2783, koszt=164,59 zł, konwersje=2.5, wartość konwersji=450.75.",
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
          blocked_claims: ["koszt pozyskania celu", "zwrot z reklam", "marnowanie budżetu na zapytaniach", "zmarnowany budżet"]
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
      blocked_claims: ["koszt pozyskania celu", "zwrot z reklam", "marnowanie budżetu na zapytaniach", "zmarnowany budżet"],
      blocked_claim_labels: [
        "koszt pozyskania celu",
        "zwrot z reklam",
        "marnowanie budżetu na zapytaniach",
        "zmarnowany budżet"
      ],
      risk: "low"
    },
    {
      id: "ads_review_campaign_triage",
      decision_type: "review_campaign_triage",
      status: "ready",
      title: "Ustal kolejność oceny kampanii Ads",
      summary:
        "WILQ połączył campaign activity, KPI, budżet, rekomendacje i impression share dla 1 kampanii.",
      rationale:
        "Triage pokazuje, którą kampanię sprawdzić najpierw, bez obietnic o marnowaniu budżetu albo opłacalności.",
      next_step:
        "Sprawdź cel kampanii, jakość konwersji, budżet, listy wyszukiwanych haseł i rekomendacje bez zapisu zmian.",
      priority: 18,
      metric_tiles: {
        kampanie: 1,
        pilne: 1,
        wysokie: 0,
        rekomendacje: 1,
        podglądy: 2
      },
      allowed_metrics: [
        "clicks",
        "impressions",
        "cost_micros",
        "conversions",
        "conversion_value",
        "ctr",
        "average_cpc_micros",
        "conversion_rate",
        "cost_per_conversion_micros",
        "roas",
        "spend_to_budget_ratio_7d",
        "search_budget_lost_impression_share",
        "recommendation_count"
      ],
      missing_read_contracts: ["target_roas_or_cpa", "human_strategy_review"],
      operator_review_gates: [
        "review_campaign_goal",
        "review_conversion_quality",
        "review_budget_context",
        "review_search_terms_before_budget_decision",
        "human_strategy_review"
      ],
      source_connectors: ["google_ads"],
      evidence_ids: ["ev_refresh_refresh_google_ads_test"],
      metric_facts: [],
      campaign_rows: [],
      campaign_triage_rows: [
        {
          campaign_id: "123",
          campaign_name: "Ekologus Search",
          campaign_status: "ENABLED",
          advertising_channel_type: "SEARCH",
          review_priority: "pilne",
          review_score: 90,
          review_reason:
            "Kolejność oceny kampanii wynika z kosztu, kliknięć, konwersji, budżetu, rekomendacji i impression share.",
          next_step:
            "Sprawdź cel kampanii, jakość konwersji, budżet, listy wyszukiwanych haseł i rekomendacje bez zapisu zmian.",
          target_status: "no_target",
          target_status_label: "brak celu",
          clicks: 107,
          impressions: 2783,
          cost_micros: 164591174,
          conversions: 2.5,
          conversion_value: 450.75,
          ctr: 0.038448,
          average_cpc_micros: 1538235.271028,
          conversion_rate: 0.023364,
          cost_per_conversion_micros: 65836469.6,
          roas: 2.738589,
          spend_to_budget_ratio_7d: 0.783768,
          search_budget_lost_impression_share: 0.18,
          recommendation_count: 1,
          recommendation_types: ["CAMPAIGN_BUDGET"],
          has_budget_apply_preview: true,
          has_recommendation_apply_preview: true,
          evidence_ids: ["ev_refresh_refresh_google_ads_test"],
          action_ids: ["act_prepare_ads_campaign_review_queue"],
          source_metric_names: [
            "clicks",
            "conversion_value",
            "conversions",
            "cost_micros",
            "impressions",
            "budget_amount_micros",
            "recommendation_available",
            "search_budget_lost_impression_share"
          ],
          missing_read_contracts: ["target_roas_or_cpa", "human_strategy_review"],
          blocked_claims: [
            "zmarnowany budżet",
            "opłacalność",
            "skalowanie budżetu",
            "zmiana budżetu",
            "zapis rekomendacji",
            "zapis zmian kampanii"
          ],
          human_review_gates: [
            "review_campaign_goal",
            "review_conversion_quality",
            "review_budget_context",
            "review_search_terms_before_budget_decision",
            "human_strategy_review"
          ]
        }
      ],
      derived_kpi_rows: [],
      budget_rows: [],
      shared_budget_distribution_rows: [],
      budget_apply_preview: [],
      recommendation_rows: [],
      recommendation_apply_preview: [],
      impression_share_rows: [],
      change_history_rows: [],
      search_term_rows: [],
      search_term_safety_rows: [],
      keyword_match_context_rows: [],
      custom_segment_candidates: [],
      custom_segment_payload_preview: [],
      negative_keyword_candidates: [],
      negative_keyword_payload_preview: [],
      action_ids: ["act_prepare_ads_campaign_review_queue"],
      knowledge_card_ids: ["card_google_ads_budget_review_playbook"],
      expert_rule_ids: ["ads_diagnostics_v1", "ads_scaling_candidates_v1"],
      blocked_claims: [
        "zmarnowany budżet",
        "opłacalność",
        "skalowanie budżetu",
        "zmiana budżetu",
        "zapis rekomendacji",
        "zapis zmian kampanii"
      ],
      risk: "medium"
    },
    {
      id: "ads_review_business_context",
      decision_type: "review_business_context",
      status: "blocked",
      title: "Uzupełnij kontekst biznesowy przed decyzjami Ads",
      summary:
        "WILQ ma live metryki Google Ads, ale nie ma kompletnego lokalnego kontekstu biznesowego.",
      rationale:
        "Google Ads pokazuje koszt, kliknięcia, konwersje i część KPI, ale nie zna marży, celu sprzedażowego ani intencji budżetu Ekologus.",
      next_step:
        "Uzupełnij nie-sekretne wartości w repo-local .env: WILQ_ADS_PROFIT_MARGIN, WILQ_ADS_BUSINESS_GOAL, WILQ_ADS_BUDGET_GOAL oraz WILQ_ADS_TARGET_ROAS albo WILQ_ADS_TARGET_CPA_MICROS.",
      priority: 22,
      metric_tiles: {
        braki: 4,
        blokady: 6,
        "ustawione pola": 0
      },
      allowed_metrics: [],
      missing_read_contracts: [
        "profit_margin",
        "business_goal",
        "human_budget_goal",
        "target_roas_or_cpa"
      ],
      source_connectors: ["google_ads"],
      evidence_ids: ["ev_refresh_refresh_google_ads_test"],
      metric_facts: [],
      campaign_rows: [],
      derived_kpi_rows: [],
      budget_rows: [],
      shared_budget_distribution_rows: [],
      budget_apply_preview: [],
      recommendation_rows: [],
      recommendation_apply_preview: [],
      impression_share_rows: [],
      change_history_rows: [],
      search_term_rows: [],
      search_term_safety_rows: [],
      keyword_match_context_rows: [],
      custom_segment_candidates: [],
      custom_segment_payload_preview: [],
      negative_keyword_candidates: [],
      negative_keyword_payload_preview: [],
      action_ids: [],
      knowledge_card_ids: [
        "card_google_ads_budget_review_playbook",
        "card_goal_001_rules"
      ],
      expert_rule_ids: ["ads_scaling_candidates_v1", "ads_principles_v1"],
      blocked_claims: [
        "opłacalność",
        "ocena marży",
        "skalowanie budżetu",
        "zmiana budżetu",
        "zapis rekomendacji",
        "zmarnowany budżet"
      ],
      risk: "medium"
    },
    {
      id: "ads_review_recommendations",
      decision_type: "review_recommendations",
      status: "ready",
      title: "Przejrzyj rekomendacje Google Ads bez zapisu zmian",
      summary:
        "WILQ ma 1 aktywną rekomendację Google Ads do sprawdzenia. Typy: CAMPAIGN_BUDGET. Podgląd wpływu dostępny dla 1; podgląd zmian dla 1.",
      rationale:
        "Google Ads recommendations są sygnałem do kontroli, nie automatyczną strategią.",
      next_step:
        "Potraktuj rekomendacje Google jako input do review, nie jako gotową strategię.",
      priority: 35,
      metric_tiles: {
        rekomendacje: 1,
        pilne: 1,
        wysokie: 0,
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
      missing_read_contracts: ["change_history"],
      operator_review_gates: [
        "human_strategy_review",
        "review_recommendation_type",
        "review_impact_metrics",
        "review_change_history",
        "review_business_goal",
        "recommendation_apply_preview",
        "google_ads_rmf_compliance_review",
        "human_confirm_before_apply"
      ],
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
          review_priority: "pilne",
          review_score: 70,
          review_reason:
            "Rekomendacja CAMPAIGN_BUDGET: podgląd wpływu: kliknięcia delta=+5, koszt delta=2.00, konwersje delta=brak. To jest kolejność przeglądu rekomendacji, nie zgoda na zapis zmian ani obietnica poprawy wyniku.",
          human_review_gates: [
            "sprawdź typ rekomendacji",
            "sprawdź metryki wpływu",
            "porównaj z historią zmian",
            "porównaj z celem biznesowym",
            "zweryfikuj RMF/compliance",
            "potwierdź człowiekiem przed zapisem"
          ],
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
            reason: "Podgląd zmian dla rekomendacji Google Ads jest do sprawdzenia w WILQ.",
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
              "zapis rekomendacji",
              "automatyczne przyjęcie rekomendacji",
              "zmiana budżetu",
              "zapis zmian kampanii",
              "obietnica poprawy wyniku"
            ],
            api_mutation_ready: false,
            apply_allowed: false,
            destructive: false
          },
          missing_metrics: [],
          blocked_claims: [
            "zapis rekomendacji",
            "automatyczne przyjęcie rekomendacji",
            "zmiana budżetu",
            "zapis zmian kampanii"
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
          reason: "Podgląd zmian dla rekomendacji Google Ads jest do sprawdzenia w WILQ.",
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
            "zapis rekomendacji",
            "automatyczne przyjęcie rekomendacji",
            "zmiana budżetu",
            "zapis zmian kampanii",
            "obietnica poprawy wyniku"
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
        "zapis rekomendacji",
        "automatyczne przyjęcie rekomendacji",
        "zmiana budżetu",
        "zapis zmian kampanii",
        "obietnica poprawy wyniku"
      ],
      blocked_claim_labels: [
        "zapis rekomendacji",
        "automatyczne przyjęcie rekomendacji",
        "zmiana budżetu",
        "zapis zmian kampanii",
        "obietnica poprawy wyniku"
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
            "skalowanie budżetu",
            "zmiana budżetu",
            "zmarnowany budżet",
            "obietnica poprawy wyniku"
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
        "skalowanie budżetu",
        "zmiana budżetu",
        "zmarnowany budżet",
        "obietnica poprawy wyniku",
        "zapis zmian kampanii"
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
            "wpływ zmian",
            "obietnica poprawy wyniku",
            "zmiana budżetu",
            "zapis zmian kampanii"
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
        "wpływ zmian",
        "obietnica poprawy wyniku",
        "zmiana budżetu",
        "zapis zmian kampanii"
      ],
      risk: "medium"
    },
    {
      id: "ads_review_search_terms",
      decision_type: "review_search_terms",
      status: "ready",
      title: "Przejrzyj zapytania z reklam bez automatycznych wykluczeń",
      summary:
        "WILQ ma 1 wierszy zapytań: kliknięcia=12, wyświetlenia=140, koszt=9,00 zł, konwersje=1, wartość konwersji=120.",
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
          blocked_claims: ["koszt pozyskania celu", "zwrot z reklam", "dodanie wykluczających słów kluczowych", "zmarnowany budżet"]
        }
      ],
      custom_segment_candidates: [],
      search_term_safety_rows: [],
      negative_keyword_candidates: [],
      negative_keyword_payload_preview: [],
      action_ids: [],
      blocked_claims: ["koszt pozyskania celu", "zwrot z reklam", "dodanie wykluczających słów kluczowych", "zmarnowany budżet"],
      risk: "medium"
    },
    {
      id: "ads_review_search_term_safety",
      decision_type: "review_search_term_safety",
      status: "ready",
      title: "Sprawdź 90-dniową historię zapytań przed wykluczeniami",
      summary:
        "WILQ ma 90-dniowy odczyt bezpieczeństwa dla 1 zapytań: kliknięcia=10, wyświetlenia=120, koszt=8,00 zł, konwersje=0, wartość konwersji=0.",
      rationale:
        "WILQ ma oddzielny 90-dniowy odczyt listy wyszukiwanych haseł jako hamulec bezpieczeństwa.",
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
        "keyword match context"
      ],
      operator_review_gates: ["human_intent_review"],
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
          blocked_claims: ["koszt pozyskania celu", "zwrot z reklam", "dodanie wykluczających słów kluczowych", "zmarnowany budżet"]
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
      blocked_claims: ["dodanie wykluczających słów kluczowych", "marnowanie budżetu na zapytaniach", "koszt pozyskania celu", "zwrot z reklam"],
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
      next_step: "Przejrzyj propozycje do sprawdzenia przed podglądem zmian.",
      allowed_metrics: [
        "search_term",
        "search_term_clicks",
        "search_term_cost_micros",
        "search_term_conversions"
      ],
      missing_read_contracts: ["keyword match context"],
      operator_review_gates: ["human_intent_review"],
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
          blocked_claims: ["koszt pozyskania celu", "zwrot z reklam", "dodanie wykluczających słów kluczowych", "zmarnowany budżet"]
        }
      ],
      custom_segment_candidates: [],
      negative_keyword_candidates: [
        {
          id: "ads_negative_keyword_review_123_789_odpady_cena",
          search_term: "odpady cena",
          review_priority: "wysokie",
          review_score: 53,
          review_reason:
            "Bieżący read: kliknięcia=6, koszt=5.00, konwersje=0; 90 dni: kliknięcia=10, koszt=8.00, konwersje=0; kontekst keywords=1 rows. To jest kolejność review, nie ocena zmarnowanego budżetu.",
          human_review_gates: [
            "sprawdź intencję zapytania",
            "porównaj z istniejącymi keywords i match types",
            "sprawdź 90-dniowy safety read",
            "zatwierdź poziom wykluczenia przed zapisem"
          ],
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
            blocked_claims: ["dodanie wykluczających słów kluczowych", "marnowanie budżetu na zapytaniach"],
            api_mutation_ready: false,
            apply_allowed: false,
            destructive: false
          },
          required_checks: [
            "review_search_term_context",
            "check_existing_keywords_and_match_types",
            "90_day_safety_check",
            "negative_keyword_change_preview",
            "human_confirm_before_apply"
          ],
          safety_status: "read_ready_needs_human_review",
          validation_status: "pending_validation",
          blocked_claims: ["dodanie wykluczających słów kluczowych", "marnowanie budżetu na zapytaniach", "koszt pozyskania celu", "zwrot z reklam"],
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
          blocked_claims: ["dodanie wykluczających słów kluczowych", "marnowanie budżetu na zapytaniach"],
          api_mutation_ready: false,
          apply_allowed: false,
          destructive: false
        }
      ],
      action_ids: ["act_prepare_negative_keyword_review_queue"],
      blocked_claims: ["dodanie wykluczających słów kluczowych", "marnowanie budżetu na zapytaniach", "koszt pozyskania celu", "zwrot z reklam"],
      risk: "medium"
    },
    {
      id: "ads_prepare_custom_segments_from_search_terms",
      decision_type: "prepare_custom_segments",
      status: "ready",
      title: "Przygotuj segmenty z realnych wyszukiwanych haseł",
      summary: "WILQ ma 1 propozycję segmentu, 1 wyszukiwane hasło z dowodów Google Ads oraz 1 pomysł Keyword Planner.",
      rationale: "WILQ ma wyszukiwane hasła z dowodów Google Ads, więc może przygotować propozycje segmentów.",
      next_step: "Przejrzyj wyszukiwane hasła i sprawdź propozycję w WILQ przed zapisem zmian.",
      allowed_metrics: [
        "search_term",
        "search_term_clicks",
        "search_term_impressions",
        "keyword_planner_idea_text",
        "keyword_planner_avg_monthly_searches"
      ],
      missing_read_contracts: ["forecast_or_audience_size"],
      operator_review_gates: [
        "review_source_terms",
        "reject_brand_or_low_intent_terms",
        "keyword_planner_enrichment",
        "forecast_or_audience_size",
        "human_confirm_before_apply"
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
          blocked_claims: ["koszt pozyskania celu", "zwrot z reklam", "dodanie wykluczających słów kluczowych", "zmarnowany budżet"]
        }
      ],
      search_term_safety_rows: [],
      keyword_planner_idea_rows: [
        {
          idea_text: "bdo szkolenie",
          avg_monthly_searches: 100,
          competition: "MEDIUM",
          competition_index: 55,
          low_top_of_page_bid_micros: 1200000,
          high_top_of_page_bid_micros: 4400000,
          source_terms: ["bdo rejestracja"],
          evidence_ids: ["ev_refresh_refresh_google_ads_test"],
          metric_facts: [],
          missing_metrics: [],
          blocked_claims: [
            "rozmiar odbiorców",
            "prognoza",
            "wzrost konwersji",
            "zwrot z reklam",
            "zapis kierowania reklam"
          ]
        }
      ],
      custom_segment_candidates: [
        {
          id: "ads_custom_segment_123",
          name: "Zapytania użytkowników: Ekologus Search",
          intent: "zainteresowanie z wyszukiwanych haseł",
          review_priority: "wysokie",
          review_score: 65,
          review_reason:
            "Wyszukiwane hasła=1, kliknięcia=12, wyświetlenia=140, koszt=9.00, konwersje=1, odrzucone terminy=0. To jest kolejność oceny segmentu, nie dowód rozmiaru odbiorców, kierowania reklam ani wpływu na kampanię.",
          human_review_gates: [
            "sprawdź intencję wyszukiwanych haseł",
            "odrzuć brand, konkurencję i frazy o niskiej intencji",
            "sprawdź Keyword Planner enrichment",
            "sprawdź prognozę albo rozmiar odbiorców",
            "zatwierdź segment przed zapisem"
          ],
          source_terms: ["bdo rejestracja"],
          rejected_terms: [],
          rejection_reasons: [],
          search_term_rows: [],
          keyword_planner_ideas: [
            {
              idea_text: "bdo szkolenie",
              avg_monthly_searches: 100,
              competition: "MEDIUM",
              competition_index: 55,
              low_top_of_page_bid_micros: 1200000,
              high_top_of_page_bid_micros: 4400000,
              source_terms: ["bdo rejestracja"],
              evidence_ids: ["ev_refresh_refresh_google_ads_test"],
              metric_facts: [],
              missing_metrics: [],
              blocked_claims: [
                "rozmiar odbiorców",
                "prognoza",
                "wzrost konwersji",
                "zwrot z reklam",
                "zapis kierowania reklam"
              ]
            }
          ],
          source_connectors: ["google_ads"],
          evidence_ids: ["ev_refresh_refresh_google_ads_test"],
          metric_facts: [],
          confidence: "medium",
          validation_status: "pending_validation",
          payload_preview: {
            id: "preview_ads_custom_segment_123",
            custom_segment_name: "Zapytania użytkowników: Ekologus Search",
            member_type: "KEYWORD",
            source_terms: ["bdo rejestracja"],
            campaign_id: "123",
            campaign_name: "Ekologus Search",
            reason: "Podgląd segmentu odbiorców oparty na wyszukiwanych hasłach do sprawdzenia.",
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
              "rozmiar odbiorców",
              "wzrost konwersji",
              "zwrot z reklam",
              "zapis kierowania reklam",
              "skuteczność kampanii"
            ],
            safety_review: customSegmentSafetyReview("preview_ads_custom_segment_123"),
            api_mutation_ready: false,
            apply_allowed: false,
            destructive: false
          },
          blocked_claims: [
            "rozmiar odbiorców",
            "wzrost konwersji",
            "zwrot z reklam",
            "zapis kierowania reklam",
            "skuteczność kampanii"
          ],
          next_step: "Użyj tych terminów jako propozycji bez zapisu zmian."
        }
      ],
      custom_segment_payload_preview: [
        {
          id: "preview_ads_custom_segment_123",
          custom_segment_name: "Zapytania użytkowników: Ekologus Search",
          member_type: "KEYWORD",
          source_terms: ["bdo rejestracja"],
          campaign_id: "123",
          campaign_name: "Ekologus Search",
          reason: "Podgląd segmentu odbiorców oparty na wyszukiwanych hasłach do sprawdzenia.",
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
            "rozmiar odbiorców",
            "wzrost konwersji",
            "zwrot z reklam",
            "zapis kierowania reklam"
          ],
          targeting_preview: [
            {
              id: "targeting_preview_ads_custom_segment_123",
              custom_segment_preview_id: "preview_ads_custom_segment_123",
              target_scope: "campaign_context_review",
              campaign_id: "123",
              campaign_name: "Ekologus Search",
              operation_type: "custom_segment_targeting_review",
              reason: "Podgląd kontekstu kierowania reklam; zapis zmian pozostaje zablokowany.",
              required_validation: [
                "keyword_planner_enrichment",
                "forecast_or_audience_size",
                "human_confirm_before_apply",
                "mutation_audit_required"
              ],
              blocked_claims: [
                "rozmiar odbiorców",
                "wzrost konwersji",
                "zwrot z reklam",
                "zapis kierowania reklam",
                "skuteczność kampanii"
              ],
              api_mutation_ready: false,
              apply_allowed: false,
              destructive: false
            }
          ],
          safety_review: customSegmentSafetyReview("preview_ads_custom_segment_123"),
          api_mutation_ready: false,
          apply_allowed: false,
          destructive: false
        }
      ],
      custom_segment_audience_forecast_rows: [
        {
          id: "forecast_ads_custom_segment_123",
          candidate_id: "ads_custom_segment_123",
          custom_segment_name: "Zapytania użytkowników: Ekologus Search",
          status: "missing_forecast",
          forecast_available: false,
          audience_size: null,
          source_terms: ["bdo rejestracja"],
          reason:
            "Brak dowodów WILQ dla prognozy albo rozmiaru odbiorców tego segmentu.",
          evidence_ids: ["ev_refresh_refresh_google_ads_test"],
          blocked_claims: [
            "rozmiar odbiorców",
            "wzrost konwersji",
            "zwrot z reklam",
            "zapis kierowania reklam",
            "skuteczność kampanii"
          ]
        }
      ],
      negative_keyword_candidates: [],
      negative_keyword_payload_preview: [],
      action_ids: ["act_prepare_custom_segments_from_search_terms"],
      blocked_claims: ["rozmiar odbiorców", "wzrost konwersji", "zwrot z reklam", "zapis kierowania reklam"],
      risk: "medium"
    },
    {
      id: "ads_block_write_actions_without_actionobject",
      decision_type: "block_write_actions",
      status: "blocked",
      title: "Zapis zmian Ads wymaga osobnego sprawdzenia akcji",
      summary: "WILQ ma dowody z odczytu Google Ads; ścieżka zapisu nadal nie ma gotowej akcji do sprawdzenia.",
      rationale: "Zmiany budżetów, kampanii, wykluczeń i segmentów wymagają sprawdzenia.",
      next_step: "Rozszerz Ads workflow o akcję przygotowawczą.",
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
      blocked_claims: ["zmiana budżetu", "campaign creation", "dodanie wykluczających słów kluczowych"],
      risk: "medium"
    }
  ],
  sections: [
    {
      id: "ads_live_data_status",
      title: "Google Ads: live data dostępne",
      status: "ready",
      summary: "WILQ ma zapisane metryki z odczytu odczytu danych Google Ads.",
      diagnosis: "Ads Doctor może pokazać campaign i search-term metrics, ale nie kosztu pozyskania celu ani zwrotu z reklam.",
      next_step: "Analizuj tylko widoczne metryki i evidence IDs.",
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
      blocked_claims: ["koszt pozyskania celu", "zwrot z reklam", "zmarnowany budżet"],
      risk: "medium"
    },
    {
      id: "ads_campaign_overview",
      title: "Aktywność kampanii Google Ads",
      status: "ready",
      summary: "Metryki z dowodami: clicks=107, impressions=2783.",
      diagnosis: "Są live campaign rows, ale kosztu pozyskania celu ani zwrotu z reklam wymagają osobnego read contract.",
      next_step: "Sprawdź kampanie bez obietnic kosztu pozyskania celu ani zwrotu z wydatków reklamowych.",
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
      blocked_claims: ["koszt pozyskania celu", "zwrot z reklam", "zmarnowany budżet"],
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
  },
  {
    name: "ahrefs_content_gap_count",
    value: 1,
    period: "connector_refresh",
    source_connector: "ahrefs",
    evidence_id: "ev_refresh_ahrefs_gap_records",
    dimensions: {
      gap_type: "content_gap",
      keyword: "audyt środowiskowy",
      competitor_domain: "konkurent.example"
    },
    unit: null,
    collected_at: "2026-06-17T10:00:00Z",
    previous_value: 1,
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
  strict_instruction: "WILQ pokazuje tylko metryki z danych źródłowych.",
  connector_summary: { total: 1, configured: 0, missing_credentials: 1 },
  sections: [
    {
      id: "what_we_know",
      title: "Co wiemy z realnych danych",
      description: "Najważniejsze fakty z danych.",
      items: [
        {
          id: "brief_metric_wordpress",
          title: "WordPress: 16 treści w spisie",
          kind: "metric",
          priority: 21,
          source_connectors: ["wordpress_ekologus"],
          evidence_ids: ["ev_refresh_wordpress_inventory"],
          metric_facts: metricFacts,
          action_ids: [],
          summary: "WILQ widzi spis treści z WordPress.",
          next_step: "Połącz inventory z GSC/GA4.",
          risk: "low",
          blocker_reason: null
        }
      ]
    },
    {
      id: "what_blocks_us",
      title: "Co blokuje decyzje",
      description: "Blokady bezpiecznych decyzji.",
      items: [
        {
          id: "brief_status_localo_access_ready",
          title: "Dostęp Localo działa; brakuje rankingów i danych profilu firmy w Google",
          kind: "metric",
          priority: 90,
          source_connectors: ["localo"],
          evidence_ids: ["ev_refresh_refresh_localo_f1d5b9fed00c"],
          metric_facts: [],
          action_ids: [],
          summary:
            "Localo potwierdził dostęp do odczytu danych. To nadal nie jest dowód rankingów, profilu firmy w Google ani konkurencji.",
          next_step: "Nie pokazuj lokalnych rekomendacji bez konkretnych danych rankingów i profilu firmy w Google.",
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
          summary: "Publikacje LinkedIn są zablokowane przez brak dostępu do organizacji.",
          next_step: "Uzupełnij dostęp LinkedIn przed przygotowaniem propozycji postów.",
          risk: "medium",
          blocker_reason: "brakuje dostępu LinkedIn"
        }
      ]
    },
    {
      id: "safe_next_actions",
      title: "Bezpieczne następne kroki",
      description: "Akcje do sprawdzenia.",
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
          next_step: "Zweryfikuj akcję i odśwież OAuth.",
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
            "WILQ widzi Merchant metryki i kieruje operatora do sprawdzenia kolejki problemów feedu.",
          next_step:
            "Otwórz podgląd zmian dla akcji przed zmianą danych produktu.",
          risk: "medium",
          blocker_reason: null
        },
        {
          id: "brief_focus_ga4_quality",
          title: "GA4: sprawdź jakość ruchu na stronach wejścia",
          kind: "recommendation",
          priority: 75,
          source_connectors: ["google_analytics_4"],
          evidence_ids: ["ev_refresh_ga4"],
          metric_facts: [metricFacts[4]],
          action_ids: ["act_review_ga4_tracking_quality"],
          summary: "WILQ ma GA4 metryki i może ocenić jakość ruchu po odświeżeniu.",
          next_step: "Porównaj zaangażowanie i konwersje z kampaniami.",
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
          summary: "WILQ widzi kliknięcia z GSC i może zbudować kolejkę okazji contentowych.",
          next_step: "Połącz dowody zapytanie/strona ze spisem treści WordPress.",
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
  strict_instruction: "WILQ pokazuje tylko metryki z danych źródłowych.",
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
      next_step: "Sprawdź dopasowanie komunikatu, CTA i pomiar przed oceną kampanii.",
      blocked_claims: ["współczynnik konwersji", "zwrot z reklam"],
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
      next_step: "Przygotuj odświeżenie istniejącej strony i sprawdź duplikaty w WordPress.",
      blocked_claims: ["wzrost konwersji", "wpływ na przychód"],
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
      blocked_claims: ["automatyczna zmiana feedu", "ponowne zatwierdzenie produktu"],
      action_ids: ["act_review_merchant_feed_issues"]
    }
  ],
  compact_groups: [
    {
      id: "gsc_seo:content_refresh:https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/",
      title: "SEO: odśwież /europejski-zielony-lad-co-to-takiego/ (2 query)",
      meta: "SEO / odświeżenie treści / najpierw",
      diagnosis:
        "2 powiązane zapytania prowadzą do tej samej strony. Suma widocznych metryk: clicks=12, impressions=120.",
      next_step: "Przygotuj odświeżenie istniejącej strony i sprawdź duplikaty w WordPress.",
      priority: 26,
      risk: "low",
      source_connectors: ["google_search_console"],
      evidence_ids: ["ev_refresh_gsc", "ev_refresh_gsc_second"],
      action_ids: ["act_prepare_content_refresh_queue"],
      blocked_claims: ["wzrost konwersji", "wpływ na przychód"]
    },
    {
      id: "ga4:landing_page_quality:/oferta/:google / cpc",
      title: "GA4: sprawdź /oferta/ / google / cpc",
      meta: "GA4 / jakość strony wejścia / najpierw",
      diagnosis: "1 grupa ruchu GA4 wymaga sprawdzenia jakości strony wejścia.",
      next_step: "Sprawdź dopasowanie komunikatu, CTA i pomiar przed oceną kampanii.",
      priority: 25,
      risk: "low",
      source_connectors: ["google_analytics_4"],
      evidence_ids: ["ev_refresh_ga4"],
      action_ids: ["act_review_ga4_tracking_quality"],
      blocked_claims: ["współczynnik konwersji", "zwrot z reklam"]
    },
    {
      id: "merchant:merchant_feed_triage:availability_updated:n:availability:",
      title: "Merchant: sprawdź availability updated / n:availability",
      meta: "Merchant / triage feedu / najpierw",
      diagnosis: "1 problem feedu Merchant wymaga review.",
      next_step: "Przygotuj kolejkę przeglądu bez zmiany głównego feedu.",
      priority: 27,
      risk: "medium",
      source_connectors: ["google_merchant_center"],
      evidence_ids: ["ev_refresh_merchant_feed"],
      action_ids: ["act_review_merchant_feed_issues"],
      blocked_claims: ["automatyczna zmiana feedu", "ponowne zatwierdzenie produktu"]
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
  strict_instruction: "WILQ pokazuje tylko metryki z danych źródłowych.",
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
  connector_status_label: "dostęp skonfigurowany",
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
    summary: "Odczyt Merchant Center zakończony.",
    errors: [],
    redacted: true
  },
  latest_refresh_status_label: "zakończony",
  live_data_available: true,
  live_data_status_label: "metryki feedu dostępne",
  product_count: 10900,
  issue_count: 23,
  freshness_assessment: {
    state: "fresh",
    state_label: "dane świeże",
    checked_at: "2026-06-17T10:00:02Z",
    latest_refresh_id: "refresh_google_merchant_center_test",
    latest_refresh_completed_at: "2026-06-17T10:00:01Z",
    age_hours: 0,
    stale_after_hours: 48,
    requires_refresh: false,
    summary: "Ostatni odczyt danych Merchant mieści się w progu świeżości.",
    next_step: "Można użyć danych do kolejki review bez dodatkowego refreshu."
  },
  unknowns: [
    {
      id: "merchant_unique_product_count_unknown",
      title: "Licznik problemów nie jest liczbą unikalnych produktów",
      reason:
        "Merchant diagnostics pokazuje wystąpienia problemów w raportach, a nie pełną deduplikowaną listę SKU.",
      impact:
        "WILQ może przygotować kolejkę review po klastrach i pokazać próbki, ale nie wolno traktować sum raportowych jako unikalnych produktów.",
      next_step:
        "Użyj próbek do ręcznego review, a pełną listę produktów potwierdź w Merchant Center albo osobnym read contract.",
      blocked_claims: ["naprawa pojedynczego produktu", "zapis do feedu", "automatyczna zmiana feedu"],
      blocked_claim_labels: ["naprawa pojedynczego produktu", "zapis do feedu", "automatyczna zmiana feedu"]
    },
    {
      id: "merchant_product_performance_join_missing",
      title: "Brak połączenia produktów Merchant z Ads/GA4",
      reason:
        "Merchant diagnostics ma przykładowe produkty, ale brakuje dopasowanych faktów Ads/GA4 po product_id albo item_id.",
      impact:
        "WILQ może prowadzić review feedu, ale nie może wskazać zwrotu z reklam na poziomie produktu ani wpływu naprawy na przychód.",
      next_step:
        "Dodać skuteczność produktu dla Google Ads Shopping, Performance Max i GA4 ecommerce.",
      blocked_claims: ["zwrot z reklam na poziomie produktu", "odzyskany przychód produktu", "efekt naprawy produktu"],
      blocked_claim_labels: ["zwrot z reklam na poziomie produktu", "odzyskany przychód produktu", "efekt naprawy produktu"]
    }
  ],
  product_sample_readiness: {
    status: "ready",
    status_label: "próbki produktów dostępne",
    sample_products_available: true,
    sample_count: 2,
    sample_product_ids: ["online~pl~PL~SKU-001", "online~pl~PL~SKU-002"],
    sample_product_titles: ["Sorbent chemiczny 10 kg"],
    current_read_contract: "merchant_aggregate_product_statuses",
    required_read_contracts: [
      "merchant_products_list_product_status",
      "merchant_reports_product_view_issue_filter"
    ],
    source_endpoint: "aggregateProductStatuses",
    summary:
      "Merchant diagnostics ma przykładowe produkty do review, ale nie jest pełną listą SKU do edycji.",
    next_step:
      "Użyj próbek jako punktu startu przeglądu i nie zapisuj zmian feedu bez podglądu zmian.",
    blocked_claims: ["naprawa pojedynczego produktu", "zapis do feedu", "automatyczna zmiana feedu"],
    blocked_claim_labels: ["naprawa pojedynczego produktu", "zapis do feedu", "automatyczna zmiana feedu"]
  },
  product_performance_readiness: {
    id: "merchant_product_performance_readiness",
    status: "blocked",
    status_label: "dane Ads/GA4 zablokowane",
    joined_product_count: 0,
    merchant_sample_count: 2,
    ads_product_fact_count: 0,
    ga4_product_fact_count: 0,
    current_read_contracts: ["merchant_aggregate_product_statuses"],
    required_read_contracts: [
      "merchant_product_id_join_key",
      "google_ads_shopping_product_performance",
      "ga4_item_product_performance"
    ],
    missing_read_contracts: [
      "merchant_product_id_join_key",
      "google_ads_shopping_product_performance",
      "ga4_item_product_performance"
    ],
    join_key_candidates: ["product_id", "item_id", "offer_id"],
    sample_product_ids: ["online~pl~PL~SKU-001", "online~pl~PL~SKU-002"],
    performance_rows: [],
    source_connectors: ["google_merchant_center"],
    evidence_ids: ["ev_refresh_merchant_feed"],
    summary:
      "Merchant ma próbki produktów, ale WILQ nie ma jeszcze dopasowanych faktów produktu z Ads/GA4.",
    next_step:
      "Dodać skuteczność produktu dla Google Ads Shopping, Performance Max i GA4 ecommerce ze wspólnym kluczem produktu.",
    blocked_claims: [
      "zwrot z reklam na poziomie produktu",
      "odzyskany przychód produktu",
      "efekt naprawy produktu",
      "skalowanie produktu w reklamach produktowych i Performance Max",
      "ponowne zatwierdzenie produktu",
      "zapis do feedu"
    ],
    blocked_claim_labels: [
      "zwrot z reklam na poziomie produktu",
      "odzyskany przychód produktu",
      "efekt naprawy produktu",
      "skalowanie produktu w reklamach produktowych i Performance Max",
      "ponowne zatwierdzenie produktu",
      "zapis do feedu"
    ]
  },
  price_impact_readiness: {
    id: "merchant_price_impact_readiness",
    status: "blocked",
    status_label: "wpływ ceny zablokowany",
    products_with_current_price: 0,
    products_with_previous_price: 0,
    products_with_price_change: 0,
    products_with_unchanged_price_history: 0,
    products_with_performance_metrics: 0,
    current_read_contracts: ["merchant_aggregate_product_statuses"],
    required_read_contracts: [
      "google_ads_shopping_product_current_price",
      "google_ads_shopping_product_price_history",
      "merchant_price_change_event_or_snapshot",
      "google_ads_or_ga4_product_performance_window"
    ],
    missing_read_contracts: [
      "google_ads_shopping_product_current_price",
      "google_ads_shopping_product_price_history",
      "merchant_price_change_event_or_snapshot",
      "google_ads_or_ga4_product_performance_window"
    ],
    payload_preview: [],
    source_connectors: ["google_merchant_center"],
    evidence_ids: ["ev_refresh_merchant_feed"],
    summary:
      "Brak historii ceny i okna performance, więc WILQ nie ocenia wpływu zmian cen na produkt.",
    next_step:
      "Dodać historię ceny i okno skuteczności produktu przed oceną wpływu zmiany ceny.",
    blocked_claims: ["wpływ zmiany ceny", "zwrot z reklam na poziomie produktu", "odzyskany przychód produktu"],
    blocked_claim_labels: ["wpływ zmiany ceny", "zwrot z reklam na poziomie produktu", "odzyskany przychód produktu"]
  },
  operator_summary: {
    id: "merchant_operator_summary",
    title: "Co marketer ma zrobić teraz z feedem",
    summary:
      "WILQ grupuje problemy Merchant po typie i atrybucie. To jest kolejka przeglądu: można przygotować decyzje i podgląd zmian, ale nie wolno obiecać ponownego zatwierdzenia produktu ani automatycznie nadpisać feedu.",
    next_step:
      "Przejdź przez top decyzje lub klastry problemów, przygotuj akcję do sprawdzenia i nie zapisuj zmian feedu bez sprawdzenia w WILQ oraz zgody operatora.",
    top_decision_ids: [
      "merchant_decision_merchant_issue_pl_not_impacted_availability_updated_n_availability"
    ],
    top_issue_cluster_ids: ["merchant_issue_pl_not_impacted_availability_updated_n_availability"],
    top_tactical_item_ids: ["tq_merchant_issue"],
    reported_issue_occurrences: 23,
    decision_source: "decision_queue",
    decision_source_label: "kolejka decyzji Merchant",
    drilldown_source: "issue_clusters",
    drilldown_source_label: "grupy problemów feedu",
    count_semantics: "reported_issue_occurrences",
    count_semantics_label: "wystąpienia problemów w raportach",
    issue_types: ["zmiana dostępności do sprawdzenia"],
    source_connectors: ["google_merchant_center"],
    evidence_ids: ["ev_refresh_merchant_feed"],
    action_ids: ["act_review_merchant_feed_issues"],
    blocked_claims: [
      "ponowne zatwierdzenie produktu",
      "odzyskany przychód",
      "automatyczna zmiana feedu",
      "nadpisanie głównego feedu"
    ],
    blocked_claim_labels: [
      "ponowne zatwierdzenie produktu",
      "odzyskany przychód",
      "automatyczna zmiana feedu",
      "nadpisanie głównego feedu"
    ]
  },
  issue_clusters: [
    {
      id: "merchant_issue_pl_not_impacted_availability_updated_n_availability",
      issue_type: "availability_updated",
      issue_type_label: "zmiana dostępności do sprawdzenia",
      severity: "NOT_IMPACTED",
      severity_label: "bez wpływu",
      resolution: "MERCHANT_ACTION",
      resolution_label: "wymaga działania po stronie Merchant",
      affected_attribute: "n:availability",
      affected_attribute_label: "dostępność",
      country: "PL",
      reporting_context: "SHOPPING_ADS",
      reporting_context_label: "reklamy produktowe",
      product_count: 23,
      count_semantics: "reported_issue_occurrences",
      sample_product_ids: ["online~pl~PL~SKU-001", "online~pl~PL~SKU-002"],
      sample_titles: ["Sorbent chemiczny 10 kg"],
      sample_unavailable_reason: null,
      source_connectors: ["google_merchant_center"],
      evidence_ids: ["ev_refresh_merchant_feed"],
      blocked_claims: ["ponowne zatwierdzenie produktu", "odzyskany przychód", "automatyczna zmiana feedu"],
      action_id: "act_review_merchant_feed_issues",
      risk: "medium",
      next_step:
        "Przejrzyj tę grupę problemu przez akcję do sprawdzenia; najpierw przygotuj podgląd zmian, bez automatycznej zmiany feedu."
    }
  ],
  decision_queue: [
    {
      id: "merchant_decision_merchant_issue_pl_not_impacted_availability_updated_n_availability",
      decision_type: "review_issue_cluster",
      decision_type_label: "przegląd problemu feedu",
      status: "ready",
      status_label: "gotowe",
      title: "Merchant: sprawdź zmiana dostępności do sprawdzenia / dostępność",
      summary:
        "23 zgłoszeń problemu bez wpływu / wymaga działania po stronie Merchant dla PL / reklamy produktowe.",
      cluster_id: "merchant_issue_pl_not_impacted_availability_updated_n_availability",
      issue_cluster_ids: ["merchant_issue_pl_not_impacted_availability_updated_n_availability"],
      issue_type: "availability_updated",
      issue_type_label: "zmiana dostępności do sprawdzenia",
      severity: "NOT_IMPACTED",
      severity_label: "bez wpływu",
      resolution: "MERCHANT_ACTION",
      resolution_label: "wymaga działania po stronie Merchant",
      affected_attribute: "n:availability",
      affected_attribute_label: "dostępność",
      country: "PL",
      reporting_context: "SHOPPING_ADS",
      reporting_context_label: "reklamy produktowe",
      product_count: 23,
      issue_count: 23,
      count_semantics: "reported_issue_occurrences",
      priority: 23,
      metric_tiles: {
        zgłoszenia: 23
      },
      sample_product_ids: ["online~pl~PL~SKU-001", "online~pl~PL~SKU-002"],
      sample_titles: ["Sorbent chemiczny 10 kg"],
      source_connectors: ["google_merchant_center"],
      evidence_ids: ["ev_refresh_merchant_feed"],
      metric_facts: [metricFacts[3]],
      action_ids: ["act_review_merchant_feed_issues"],
      blocked_claims: ["ponowne zatwierdzenie produktu", "odzyskany przychód", "automatyczna zmiana feedu"],
      blocked_claim_labels: ["ponowne zatwierdzenie produktu", "odzyskany przychód", "automatyczna zmiana feedu"],
      rationale:
        "To jest klaster problemu Merchant do ręcznego review. Liczba oznacza wystąpienia problemu w raportach, nie gotową zmianę feedu. Przykładowe produkty służą tylko do ręcznego sprawdzenia problemu.",
      next_step:
        "Przejrzyj tę grupę problemu przez akcję do sprawdzenia; najpierw przygotuj podgląd zmian, bez automatycznej zmiany feedu.",
      risk: "medium",
      risk_label: "średnie ryzyko"
    }
  ],
  sections: [
    {
      id: "merchant_feed_health",
      label: "Metryki produktów",
      title: "Merchant Center: stan produktów i feedu",
      status: "ready",
      status_label: "gotowe",
      summary: "Metryki Merchant: total_products=10900, item_level_issue_count=23.",
      diagnosis: "WILQ ma metryki Merchant z odczytu i może ocenić skalę feedu.",
      next_step: "Przejdź do kolejki problemów i grupuj je po typie.",
      source_connectors: ["google_merchant_center"],
      evidence_ids: ["ev_refresh_merchant_feed"],
      metric_facts: [metricFacts[2], metricFacts[3]],
      tactical_items: [],
      action_ids: ["act_review_merchant_feed_issues"],
      blocked_claims: ["ponowne zatwierdzenie produktu", "odzyskany przychód"],
      blocked_claim_labels: ["ponowne zatwierdzenie produktu", "odzyskany przychód"],
      risk: "medium",
      risk_label: "średnie ryzyko"
    },
    {
      id: "merchant_issue_queue",
      label: "Kolejka problemów feedu",
      title: "Merchant Center: kolejka problemów feedu",
      status: "ready",
      status_label: "gotowe",
      summary:
        "WILQ ma 1 grupę problemów feedu, 1 taktykę Merchant i 1 metrykę problemu. Liczby w grupach są wystąpieniami problemu w raportach, nie gwarancją unikalnych produktów.",
      diagnosis: "Najbezpieczniejsza praca to przegląd problemów po typie.",
      next_step: "Otwórz akcję `act_review_merchant_feed_issues`.",
      source_connectors: ["google_merchant_center"],
      evidence_ids: ["ev_refresh_merchant_feed"],
      metric_facts: [metricFacts[3]],
      tactical_items: [tacticalQueue.items[2]],
      action_ids: ["act_review_merchant_feed_issues"],
      blocked_claims: ["automatyczna zmiana feedu", "nadpisanie głównego feedu"],
      blocked_claim_labels: ["automatyczna zmiana feedu", "nadpisanie głównego feedu"],
      risk: "medium",
      risk_label: "średnie ryzyko"
    }
  ],
  evidence_ids: [
    "ev_refresh_merchant_feed",
    "ev_refresh_merchant_issue_clusters",
    "ev_refresh_merchant_safety"
  ],
  action_ids: ["act_review_merchant_feed_issues"],
  blocker_count: 0
};

const contentDiagnostics = {
  generated_at: "2026-06-17T10:00:00Z",
  language: "pl-PL",
  strict_instruction: "WILQ pokazuje tylko metryki z danych źródłowych.",
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
    },
    {
      id: "ahrefs",
      label: "Ahrefs",
      status: "configured",
      configured: true,
      missing_credentials: [],
      available_credential_sources: ["repo_env"],
      freshness: { state: "fresh" },
      supported_actions: ["content_gap_review"]
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
      summary: "Odczyt GSC zakończony.",
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
      summary: "Spis treści WordPress odczytany.",
      errors: [],
      redacted: true
    },
    {
      id: "refresh_ahrefs_gap_records_test",
      connector_id: "ahrefs",
      mode: "vendor_read",
      status: "completed",
      started_at: "2026-06-17T10:00:00Z",
      completed_at: "2026-06-17T10:00:01Z",
      evidence_ids: ["ev_refresh_ahrefs_gap_records"],
      missing_credentials: [],
      checked_credentials: ["AHREFS_API_TOKEN"],
      external_call_attempted: true,
      vendor_data_collected: true,
      metric_summary: { ahrefs_content_gap_count: 1 },
      summary: "Dane luk Ahrefs odczytane.",
      errors: [],
      redacted: true
    }
  ],
  live_data_available: true,
  query_page_count: 1,
  matched_inventory_count: 1,
  operator_summary: {
    id: "content_operator_summary",
    title: "Co marketer ma zrobić teraz z treściami",
      summary:
      "WILQ łączy zapytania i URL-e z GSC ze spisem treści WordPress. Najpierw obsłuż istniejące URL-e i klastry zapytań, potem dopiero twórz nowe treści. Bez dowodów nie wolno twierdzić, że wzrosną leady, pozycje albo konwersje.",
    next_step:
      "Przejdź przez top decyzje contentowe, wybierz odświeżenie, scalenie, utworzenie albo blokadę i sprawdź w WILQ tylko akcje do sprawdzenia.",
    top_decision_ids: [
      "content_decision_ahrefs_gap_records_review",
      "content_decision_https_www_ekologus_pl_bdo"
    ],
    confirmed_wordpress_count: 1,
    missing_wordpress_count: 0,
    current_site_match_count: 1,
    decision_type_labels: ["sprawdzenie luk Ahrefs", "odświeżenie albo scalenie"],
    source_connectors: ["ahrefs", "google_search_console", "wordpress_ekologus"],
    evidence_ids: [
      "ev_refresh_ahrefs_gap_records",
      "ev_refresh_gsc",
      "ev_refresh_wordpress_inventory"
    ],
    action_ids: ["act_prepare_content_refresh_queue"],
    blocked_claims: [
      "wzrost liczby leadów",
      "wzrost konwersji",
      "gwarancja pozycji",
      "wzrost ruchu"
    ]
  },
  decision_queue: [
    {
      id: "content_decision_https_www_ekologus_pl_bdo",
      decision_type: "refresh_or_merge",
      decision_type_label: "odświeżenie albo scalenie",
      status: "ready",
      title: 'SEO: odśwież lub scal "bdo" (1 zapytanie)',
      summary:
        'GSC: 120 wyświetleń, 12 kliknięć, CTR 10.00%; główne zapytanie: "bdo". WordPress potwierdza istniejącą stronę, więc to jest decyzja odświeżenia albo scalenia, nie nowy artykuł.',
      priority: 23,
      metric_tiles: {
        zapytania: 1,
        WP: "znaleziono",
        wyświetlenia: 120,
        kliknięcia: 12,
        CTR: "10.00%",
        pozycja: 4.5
      },
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
      wordpress_match_label: "potwierdzony",
      wordpress_match_confidence: "exact_url",
      wordpress_match_confidence_label: "dokładny URL",
      wordpress_content_url: "https://www.ekologus.pl/bdo/",
      source_url: "https://www.ekologus.pl/bdo/",
      source_site_host: "www.ekologus.pl",
      source_public_url: "https://www.ekologus.pl/bdo/",
      intended_final_url: "https://www.ekologus.pl/bdo/",
      final_canonical_url: "https://www.ekologus.pl/bdo/",
      inventory_gate_status: "confirmed_current_inventory",
      inventory_gate_status_label: "spis potwierdzony na obecnej stronie",
      canonical_gate_status: "current_url_confirmed",
      canonical_gate_status_label: "obecny URL potwierdzony",
      duplicate_gate_status: "refresh_or_merge_required",
      duplicate_gate_status_label: "odśwież albo scal zamiast pisać od nowa",
      content_gate_summary:
        "Spis treści potwierdza istniejący URL. WILQ traktuje to jako odświeżenie albo scalenie, nie nowy artykuł; nowa treść pozostaje zablokowana przed kontrolą duplikacji.",
      source_connectors: ["google_search_console", "wordpress_ekologus"],
      evidence_ids: ["ev_refresh_gsc", "ev_refresh_wordpress_inventory"],
      metric_facts: [metricFacts[5]],
      action_ids: ["act_prepare_content_refresh_queue"],
      blocked_claims: ["wzrost liczby leadów", "wzrost konwersji"],
      blocked_claim_labels: ["wzrost liczby leadów", "wzrost konwersji"],
      rationale:
        "Spis treści WordPress potwierdza istniejący URL, więc WILQ kieruje to do odświeżenia albo scalenia zamiast tworzenia nowej treści.",
      next_step:
        "Przygotuj plan odświeżenia albo scalenia: title, H1/H2, sekcje brakujące wobec zapytania i CTA. Nie obiecuj leadów ani wzrostów pozycji.",
      risk: "low"
    },
    {
      id: "content_decision_ahrefs_gap_records_review",
      decision_type: "review_ahrefs_gap_records",
      decision_type_label: "sprawdzenie luk Ahrefs",
      status: "ready",
      title: "Ahrefs: zweryfikuj luki SEO przed planem treści",
      summary:
        "WILQ ma 1 rekord luk Ahrefs: luki treści=1, słowa organiczne=0, najlepsze strony=0, luki backlinków=0. Ocena jakości wskazuje 1 pasujący rekord, 0 rekordów do ręcznego sprawdzenia i 0 rekordów poza tematem. To jest materiał do sprawdzenia z GSC/WordPress, nie obietnica wzrostu ruchu.",
      priority: 18,
      metric_tiles: {
        "rekordy Ahrefs": 1,
        pasujące: 1,
        "do sprawdzenia": 0,
        "poza zakresem": 0,
        "GSC overlap": 1,
        "WP overlap": 1,
        "luki treści": 1,
        "luki backlinków": 0
      },
      page: null,
      normalized_page_path: null,
      queries: ["audyt środowiskowy"],
      query_count: 1,
      primary_query: "audyt środowiskowy",
      total_clicks: null,
      total_impressions: null,
      aggregate_ctr: null,
      best_average_position: null,
      wordpress_match: null,
      wordpress_match_label: null,
      wordpress_match_confidence: null,
      wordpress_match_confidence_label: null,
      wordpress_content_url: null,
      source_connectors: ["ahrefs"],
      evidence_ids: ["ev_refresh_ahrefs_gap_records"],
      metric_facts: [metricFacts[6]],
      ahrefs_candidate_rows: [
        {
          id: "ahrefs_candidate_audyt_srodowiskowy",
          topic: "audyt środowiskowy",
          gap_type: "content_gap",
          gap_type_label: "luka treści",
          relevance_status: "relevant",
          relevance_status_label: "pasuje",
          relevance_score: 9,
          business_relevance_reasons: [
            "ekologus_domain_term",
            "gsc_overlap",
            "wordpress_inventory_overlap",
            "content_candidate"
          ],
          business_relevance_reason_labels: [
            "pasuje do zakresu Ekologus",
            "pokrywa się z GSC",
            "pokrywa się z WordPress",
            "propozycja treści"
          ],
          gsc_demand: "present",
          gsc_demand_label: "jest",
          wordpress_inventory_match: "present",
          wordpress_inventory_match_label: "jest",
          gsc_overlap_terms: ["audyt środowiskowy"],
          wordpress_overlap_urls: ["https://www.ekologus.pl/audyt-srodowiskowy/"],
          keyword: "audyt środowiskowy",
          competitor_domain: "konkurent.example",
          source_url: null,
          target_url: null,
          metric_name: "ahrefs_content_gap_count",
          metric_value: 1,
          evidence_ids: ["ev_refresh_ahrefs_gap_records"],
          next_step:
            "Zweryfikuj `audyt środowiskowy` z GSC i spisem treści WordPress, potem zdecyduj: odświeżenie, scalenie, utworzenie albo blokada. Wspólne sygnały: GSC: audyt środowiskowy; WP: 1 URL."
        }
      ],
      action_ids: ["act_prepare_content_refresh_queue"],
      blocked_claims: [
        "rekomendacja treści poza zakresem",
        "plan treści bez kontroli trafności",
        "wzrost ruchu",
        "wzrost autorytetu",
        "gwarancja pozycji"
      ],
      blocked_claim_labels: [
        "rekomendacja treści poza zakresem",
        "plan treści bez kontroli trafności",
        "wzrost ruchu",
        "wzrost autorytetu",
        "gwarancja pozycji"
      ],
      rationale:
        "Ahrefs wskazuje luki względem konkurencji, ale ocena jakości rozdziela rekordy pasujące do zakresu Ekologus od tematów szerokich i poza zakresem.",
      next_step:
        "Najpierw przejrzyj pasujące rekordy: audyt środowiskowy. Odrzuć 0 rekordów poza zakresem i dopiero potem połącz sensowne tematy z GSC/WordPress.",
      risk: "medium"
    }
  ],
  sections: [
    {
      id: "content_query_page_matrix",
      title: "GSC: query/page matrix",
      status: "ready",
      summary: "WILQ ma 1 GSC tactical items i 1 query/page metryki.",
      diagnosis: "Query/page matrix pozwala wskazać konkretne strony i zapytania.",
      next_step: "Otwórz najwyższe priorytety i sprawdź intent oraz WordPress match.",
      source_connectors: ["google_search_console"],
      evidence_ids: ["ev_refresh_gsc"],
      metric_facts: [metricFacts[5]],
      tactical_items: [tacticalQueue.items[1]],
      action_ids: ["act_prepare_content_refresh_queue"],
      blocked_claims: ["wzrost liczby leadów", "wzrost konwersji"],
      risk: "low"
    },
    {
      id: "content_inventory_match",
      title: "WordPress: inventory protection",
      status: "ready",
      summary: "WILQ ma 1 inventory facts, 1 matched queue items i 0 missing matches.",
      diagnosis: "Spis treści WordPress chroni marketera przed pisaniem drugi raz tego samego.",
      next_step: "Najpierw obsłuż potwierdzone odświeżenia i scalenia; nowe treści twórz po kontroli duplikacji.",
      source_connectors: ["wordpress_ekologus"],
      evidence_ids: ["ev_refresh_wordpress_inventory", "ev_refresh_gsc"],
      metric_facts: [metricFacts[0]],
      tactical_items: [tacticalQueue.items[1]],
      action_ids: ["act_prepare_content_refresh_queue"],
      blocked_claims: ["nowa treść bez kontroli spisu treści"],
      risk: "low"
    }
  ],
  evidence_ids: [
    "ev_refresh_gsc",
    "ev_refresh_wordpress_inventory",
    "ev_refresh_ahrefs_gap_records",
    "ev_refresh_content_safety"
  ],
  action_ids: ["act_prepare_content_refresh_queue"],
  blocker_count: 0
};

const contentPreflight = {
  generated_at: "2026-06-17T10:00:00Z",
  language: "pl-PL",
  strict_instruction: "Bramka pisania przed planem treści i szkicem.",
  primary_item: {
    id: "preflight_content_decision_https_www_ekologus_pl_bdo",
    technical_decision_id: "content_decision_https_www_ekologus_pl_bdo",
    recommended_mode: "refresh",
    recommended_mode_label: "odświeżyć",
    status: "review_required",
    status_label: "wymaga sprawdzenia",
    create_allowed: false,
    draft_allowed: false,
    wordpress_draft_allowed: false,
    sales_brief_allowed: true,
    source_public_url: "https://www.ekologus.pl/bdo/",
    preview_url: null,
    intended_final_url: "https://www.ekologus.pl/bdo/",
    final_canonical_url: "https://www.ekologus.pl/bdo/",
    inventory_gate_status: "confirmed_current_inventory",
    inventory_gate_status_label: "spis potwierdzony na obecnej stronie",
    canonical_gate_status: "current_url_confirmed",
    canonical_gate_status_label: "obecny URL potwierdzony",
    duplicate_gate_status: "refresh_or_merge_required",
    duplicate_gate_status_label: "odśwież albo scal zamiast pisać od nowa",
    claim_gate_status: "needs_claim_review",
    claim_gate_status_label: "wymaga kontroli obietnic",
    service_mapping_status: "ready_for_service_review",
    service_mapping_status_label: "gotowe do sprawdzenia dopasowania usługi",
    similar_existing_urls: ["https://www.ekologus.pl/bdo/"],
    query_overlap_summary: "1 zapytań z GSC; główne zapytanie: bdo.",
    blocked_claims: ["wzrost liczby leadów", "wzrost konwersji"],
    missing_inputs: [],
    evidence_ids: ["ev_refresh_gsc", "ev_refresh_wordpress_inventory"],
    source_connectors: ["google_search_console", "wordpress_ekologus"],
    next_step: "Przygotuj plan odświeżenia dopiero po sprawdzeniu ryzykownych obietnic."
  },
  items: [
    {
      id: "preflight_content_decision_https_www_ekologus_pl_bdo",
      technical_decision_id: "content_decision_https_www_ekologus_pl_bdo",
      recommended_mode: "refresh",
      recommended_mode_label: "odświeżyć",
      status: "review_required",
      status_label: "wymaga sprawdzenia",
      create_allowed: false,
      draft_allowed: false,
      wordpress_draft_allowed: false,
      sales_brief_allowed: true,
      source_public_url: "https://www.ekologus.pl/bdo/",
      preview_url: null,
      intended_final_url: "https://www.ekologus.pl/bdo/",
      final_canonical_url: "https://www.ekologus.pl/bdo/",
      inventory_gate_status: "confirmed_current_inventory",
      inventory_gate_status_label: "spis potwierdzony na obecnej stronie",
      canonical_gate_status: "current_url_confirmed",
      canonical_gate_status_label: "obecny URL potwierdzony",
      duplicate_gate_status: "refresh_or_merge_required",
      duplicate_gate_status_label: "odśwież albo scal zamiast pisać od nowa",
      claim_gate_status: "needs_claim_review",
      claim_gate_status_label: "wymaga kontroli obietnic",
      service_mapping_status: "ready_for_service_review",
      service_mapping_status_label: "gotowe do sprawdzenia dopasowania usługi",
      similar_existing_urls: ["https://www.ekologus.pl/bdo/"],
      query_overlap_summary: "1 zapytań z GSC; główne zapytanie: bdo.",
      blocked_claims: ["wzrost liczby leadów", "wzrost konwersji"],
      missing_inputs: [],
      evidence_ids: ["ev_refresh_gsc", "ev_refresh_wordpress_inventory"],
      source_connectors: ["google_search_console", "wordpress_ekologus"],
      next_step: "Przygotuj plan odświeżenia dopiero po sprawdzeniu ryzykownych obietnic."
    }
  ],
  evidence_ids: ["ev_refresh_gsc", "ev_refresh_wordpress_inventory"],
  source_connectors: ["google_search_console", "wordpress_ekologus"],
  blocker_count: 0
};

const ga4Diagnostics = {
  generated_at: "2026-06-17T10:00:00Z",
  language: "pl-PL",
  strict_instruction: "WILQ pokazuje tylko metryki z danych źródłowych.",
  connector_status_label: "dostęp skonfigurowany",
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
    summary: "Odczyt GA4 zakończony.",
    errors: [],
    redacted: true
  },
  latest_refresh_status_label: "zakończony",
  live_data_available: true,
  live_data_status_label: "metryki GA4 dostępne",
  landing_group_count: 1,
  low_engagement_count: 1,
  wordpress_match_count: 0,
  freshness_assessment: {
    state: "fresh",
    state_label: "dane świeże",
    checked_at: "2026-06-17T10:00:02Z",
    latest_refresh_id: "refresh_google_analytics_4_test",
    latest_refresh_completed_at: "2026-06-17T10:00:01Z",
    age_hours: 0,
    stale_after_hours: 48,
    requires_refresh: false,
    summary: "Ostatni odczyt danych GA4 mieści się w progu świeżości.",
    next_step: "Można użyć danych GA4 do review bez dodatkowego refreshu."
  },
  conversion_readiness_contract: {
    id: "ga4_conversion_readiness_contract",
    status: "blocked",
    status_label: "blokuje wnioski o konwersjach",
    title: "GA4: gotowość konwersji i zdarzeń kluczowych",
    summary:
      "WILQ może oceniać jakość ruchu z GA4, ale obietnice konwersji, zwrotu z wydatków reklamowych, przychodu i opłacalności wymagają osobnych metryk konwersji albo zdarzeń kluczowych.",
    allowed_metrics: ["conversions", "key_events", "purchase_revenue", "total_revenue", "transactions"],
    available_read_contracts: [],
    available_read_contract_labels: [],
    missing_read_contracts: ["conversion_or_key_event_mapping"],
    missing_read_contract_labels: ["powiązanie konwersji i zdarzeń kluczowych"],
    conversion_like_metric_count: 0,
    dimensioned_behavior_metric_count: 1,
    landing_group_count: 1,
    source_connectors: ["google_analytics_4"],
    evidence_ids: ["ev_refresh_ga4"],
    action_ids: ["act_review_ga4_tracking_quality"],
    blocked_claims: ["współczynnik konwersji", "zwrot z reklam", "przychód", "opłacalność"],
    blocked_claim_labels: ["współczynnik konwersji", "zwrot z reklam", "przychód", "opłacalność"],
    next_step:
      "Sprawdź jakość pomiaru w WILQ i potwierdź powiązanie konwersji i zdarzeń kluczowych przed wnioskami o opłacalności.",
    risk: "medium"
  },
  operator_summary: {
    id: "ga4_operator_summary",
    title: "Co marketer ma sprawdzić teraz w jakości ruchu",
    summary:
      "WILQ pokazuje grupy ruchu do kontroli stron wejścia, źródeł i kampanii. Brak metryk konwersji oznacza, że nie wolno wyciągać wniosków o zwrot z reklam, przychód, spadku konwersji ani winie kampanii.",
    next_step:
      "Przejdź przez najważniejsze decyzje GA4, oddziel problem pomiaru od problemu jakości ruchu i sprawdź propozycję w WILQ tylko jako sprawdzenie bez zapisu.",
    top_decision_ids: ["ga4_decision_tq_ga4_landing"],
    measurement_issue_count: 0,
    wordpress_missing_count: 1,
    conversion_readiness_status: "blocked",
    source_connectors: ["google_analytics_4"],
    evidence_ids: ["ev_refresh_ga4"],
    action_ids: ["act_review_ga4_tracking_quality"],
    blocked_claims: ["współczynnik konwersji", "zwrot z reklam", "przychód", "opłacalność"],
    blocked_claim_labels: ["współczynnik konwersji", "zwrot z reklam", "przychód", "opłacalność"]
  },
  decision_queue: [
    {
      id: "ga4_decision_tq_ga4_landing",
      decision_type: "review_landing_mapping",
      decision_type_label: "sprawdzenie strony wejścia",
      title: "Sprawdź stronę wejścia: /oferta/",
      status: "blocked",
      status_label: "zablokowane",
      priority: 31,
      metric_tiles: { aktywni: 20, sesje: 30, zaangażowanie: "12.5%" },
      landing_page: "/oferta/",
      source_medium: "google / cpc",
      campaign_name: "Ekologus Ogólna",
      wordpress_match: "missing",
      wordpress_match_label: "brak potwierdzenia",
      wordpress_match_confidence: "missing",
      wordpress_match_confidence_label: "brak dopasowania",
      wordpress_content_url: null,
      source_connectors: ["google_analytics_4"],
      evidence_ids: ["ev_refresh_ga4"],
      metric_facts: [metricFacts[4]],
      action_ids: ["act_review_ga4_tracking_quality"],
      blocked_claims: ["współczynnik konwersji", "zwrot z reklam", "przychód", "opłacalność"],
      blocked_claim_labels: ["współczynnik konwersji", "zwrot z reklam", "przychód", "opłacalność"],
      rationale:
        "GA4 widzi ruch na stronie wejścia /oferta/, ale Spis treści WordPress nie potwierdza dopasowania URL.",
      next_step:
        "Sprawdź stronę wejścia i dopiero potem oceniaj dopasowanie komunikatu albo jakość ruchu.",
      risk: "medium",
      risk_label: "średnie ryzyko"
    }
  ],
  sections: [
    {
      id: "ga4_landing_behavior",
      label: "Jakość ruchu ze stron wejścia",
      title: "GA4: jakość ruchu ze stron wejścia",
      status: "ready",
      status_label: "gotowe",
      summary: "WILQ ma 1 grupę stron wejścia, źródeł ruchu i kampanii oraz 1 metrykę GA4.",
      diagnosis: "Fakty zachowania z GA4 pozwalają wskazać strony wejścia do kontroli jakości ruchu.",
      next_step: "Najpierw sprawdź grupy z niskim zaangażowaniem.",
      source_connectors: ["google_analytics_4"],
      evidence_ids: ["ev_refresh_ga4"],
      metric_facts: [metricFacts[4]],
      tactical_items: [tacticalQueue.items[0]],
      action_ids: ["act_review_ga4_tracking_quality"],
      blocked_claims: ["współczynnik konwersji", "zwrot z reklam", "przychód"],
      blocked_claim_labels: ["współczynnik konwersji", "zwrot z reklam", "przychód"],
      risk: "low",
      risk_label: "niskie ryzyko"
    },
    {
      id: "ga4_tracking_readiness",
      label: "Gotowość pomiaru konwersji",
      title: "GA4: gotowość pomiaru konwersji",
      status: "missing",
      status_label: "brak metryk konwersji",
      summary: "WILQ ma 1 metrykę zachowania i 0 metryk konwersji albo kluczowych zdarzeń.",
      diagnosis: "Aktualne dane wspierają review jakości ruchu, ale nie dowodzą konwersji.",
      next_step: "Sprawdź propozycję w WILQ i zatrzymaj wnioski o konwersjach bez metryk.",
      source_connectors: ["google_analytics_4"],
      evidence_ids: ["ev_refresh_ga4"],
      metric_facts: [metricFacts[4]],
      tactical_items: [tacticalQueue.items[0]],
      action_ids: ["act_review_ga4_tracking_quality"],
      blocked_claims: ["spadek konwersji", "diagnoza lejka"],
      blocked_claim_labels: ["spadek konwersji", "diagnoza lejka"],
      risk: "medium",
      risk_label: "średnie ryzyko"
    }
  ],
  evidence_ids: ["ev_refresh_ga4", "ev_refresh_ga4_tracking_review", "ev_refresh_ga4_safety"],
  action_ids: ["act_review_ga4_tracking_quality"],
  blocker_count: 1,
  decision_blocker_count: 1
};

const localoDiagnostics = {
  generated_at: "2026-06-17T10:00:00Z",
  language: "pl-PL",
  strict_instruction: "WILQ pokazuje tylko metryki z danych źródłowych.",
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
    summary: "Localo Test dostępu completed with local OAuth access token.",
    errors: [],
    redacted: true
  },
  latest_refresh_status_label: "zakończony",
  access_probe: {
    status: "access_ready",
    status_label: "dostęp działa",
    source_run_id: "refresh_localo_access_ready_test",
    mcp_initialize_status: 200,
    authorization_code_supported: true,
    authorization_code_supported_label: "tak",
    pkce_s256_supported: true,
    pkce_s256_supported_label: "tak",
    access_token_present: true,
    access_token_present_label: "obecny",
    evidence_ids: ["ev_refresh_refresh_localo_access_ready_test"],
    summary:
      "Localo potwierdził dostęp do odczytu danych. To nadal nie jest dowód rankingów, profilu firmy w Google ani konkurencji."
  },
  live_data_available: false,
  visibility_fact_count: 0,
  operator_summary: {
    id: "localo_operator_summary",
    title: "Co marketer ma wiedzieć o Localo",
    summary:
      "Ten widok pokazuje, czy Localo może już wspierać decyzje lokalnego SEO. Dostęp Localo nie jest jeszcze dowodem rankingów, profilu firmy w Google, konkurencji ani recenzji, więc WILQ blokuje obietnice bez danych widoczności.",
    next_step:
      "Użyj top decyzji jako statusu źródła. Nie proponuj lokalnych działań SEO ani zmian w profilu firmy w Google, dopóki odczyt danych Localo nie dostarczy danych widoczności.",
    top_decision_ids: [
      "localo_access_ready_wait_for_visibility_facts",
      "localo_block_visibility_claims_without_read_contract"
    ],
    access_status: "access_ready",
    access_status_label: "dostęp działa",
    visibility_fact_count: 0,
    missing_read_contracts: [
      "local_rankings",
      "gbp_visibility",
      "competitor_visibility",
      "reviews",
      "local_tasks"
    ],
    missing_read_contract_labels: [
      "rankingi lokalne",
      "widoczność profilu firmy w Google",
      "widoczność konkurencji",
      "opinie",
      "zadania lokalne"
    ],
    source_connectors: ["localo"],
    evidence_ids: ["ev_refresh_refresh_localo_access_ready_test"],
    action_ids: [],
    blocked_claims: [
      "lokalne rankingi",
      "wyniki profilu firmy w Google",
      "widoczności konkurencji",
      "poprawa widoczności lokalnej"
    ],
    blocked_claim_labels: [
      "lokalne rankingi",
      "wyniki profilu firmy w Google",
      "widoczności konkurencji",
      "poprawa widoczności lokalnej"
    ]
  },
  decision_queue: [
    {
      id: "localo_access_ready_wait_for_visibility_facts",
      decision_type: "access_ready_wait_for_visibility_facts",
      decision_type_label: "status źródła",
      status: "ready",
      status_label: "gotowe",
      title: "Dostęp Localo działa; brakuje rankingów i danych profilu firmy w Google",
      summary:
        "Localo potwierdził dostęp do odczytu danych. WILQ nie ma jeszcze lokalnych rankingów, profilu firmy w Google, konkurencji ani recenzji.",
      rationale:
        "To jest gotowość dostępu do Localo, nie diagnoza lokalnej widoczności. Marketer nie powinien traktować tego jako zadania optymalizacyjnego.",
      next_step:
        "Zostaw Localo jako status źródła i dodaj odczyt danych rankingów, profilu firmy w Google, konkurencji i recenzji.",
      access_status: "access_ready",
      access_status_label: "dostęp działa",
      priority: 30,
      priority_label: "wysoki priorytet",
      metric_tiles: {
        "dostęp Localo": 1,
        "dane Localo": 0,
        "brakujące dane": 5
      },
      allowed_evidence: ["mcp_initialize", "oauth_metadata", "access_token_presence"],
      allowed_evidence_labels: [
        "potwierdzenie dostępu Localo",
        "metadane autoryzacji",
        "obecność tokenu"
      ],
      missing_read_contracts: [
        "local_rankings",
        "gbp_visibility",
        "competitor_visibility",
        "reviews",
        "local_tasks"
      ],
      missing_read_contract_labels: [
        "rankingi lokalne",
        "widoczność profilu firmy w Google",
        "widoczność konkurencji",
        "opinie",
        "zadania lokalne"
      ],
      source_connectors: ["localo"],
      evidence_ids: ["ev_refresh_refresh_localo_access_ready_test"],
      metric_facts: [],
      action_ids: [],
      blocked_claims: [
        "lokalne rankingi",
        "wyniki profilu firmy w Google",
        "widoczności konkurencji",
        "poprawa widoczności lokalnej"
      ],
      blocked_claim_labels: [
        "lokalne rankingi",
        "wyniki profilu firmy w Google",
        "widoczności konkurencji",
        "poprawa widoczności lokalnej"
      ],
      risk: "low"
    },
    {
      id: "localo_block_visibility_claims_without_read_contract",
      decision_type: "block_visibility_claims",
      decision_type_label: "blokada obietnic",
      status: "blocked",
      status_label: "zablokowane",
      title: "Nie wyciągaj wniosków o lokalnej widoczności bez danych Localo",
      summary:
        "WILQ blokuje obietnice o rankingach, profilu firmy w Google, konkurencji, recenzjach i wzroście widoczności, dopóki Localo nie dostarczy tych danych.",
      rationale:
        "Dostęp do źródła nie jest metryką marketingową. To chroni dashboard i skille przed udawaniem lokalnej diagnozy SEO.",
      next_step:
        "Najpierw dodaj odczyt danych Localo; dopiero potem buduj lokalne akcje do sprawdzenia.",
      access_status: "access_ready",
      access_status_label: "dostęp działa",
      priority: 10,
      priority_label: "pilne",
      metric_tiles: {
        "blokady obietnic": 5,
        "brakujące dane": 5
      },
      allowed_evidence: ["mcp_initialize"],
      allowed_evidence_labels: ["potwierdzenie dostępu Localo"],
      missing_read_contracts: [
        "local_rankings",
        "gbp_visibility",
        "competitor_visibility",
        "reviews",
        "local_tasks"
      ],
      missing_read_contract_labels: [
        "rankingi lokalne",
        "widoczność profilu firmy w Google",
        "widoczność konkurencji",
        "opinie",
        "zadania lokalne"
      ],
      source_connectors: ["localo"],
      evidence_ids: ["ev_refresh_refresh_localo_access_ready_test"],
      metric_facts: [],
      action_ids: [],
      blocked_claims: [
        "lokalne rankingi",
        "wyniki profilu firmy w Google",
        "widoczności konkurencji",
        "poprawa widoczności lokalnej"
      ],
      blocked_claim_labels: [
        "lokalne rankingi",
        "wyniki profilu firmy w Google",
        "widoczności konkurencji",
        "poprawa widoczności lokalnej"
      ],
      risk: "medium"
    }
  ],
  sections: [
    {
      id: "localo_access_status",
      title: "Localo: status dostępu do danych",
      status: "ready",
      status_label: "gotowe",
      summary:
        "Localo potwierdził dostęp do odczytu danych. To nadal nie jest dowód rankingów, profilu firmy w Google ani konkurencji.",
      diagnosis: "Dostęp Localo pozwala WILQ odczytywać dane Localo.",
      next_step:
        "Nie pokazuj Localo jako zadania dziennego. Użyj tego widoku jako statusu źródła.",
      source_connectors: ["localo"],
      evidence_ids: ["ev_refresh_refresh_localo_access_ready_test"],
      metric_facts: [],
      action_ids: [],
      blocked_claims: [],
      blocked_claim_labels: [],
      risk: "low"
    },
    {
      id: "localo_visibility_contract",
      title: "Localo: dane rankingów i profilu firmy w Google",
      status: "missing",
      status_label: "brak danych",
      summary:
        "WILQ nie ma jeszcze rankingów, danych profilu firmy w Google, widoczności konkurencji ani recenzji z Localo.",
      diagnosis:
        "Brak tych danych oznacza brak lokalnej diagnozy marketingowej, nie brak problemu.",
      next_step:
        "Dodaj odczyt rankingów, profilu firmy w Google, konkurencji i recenzji zanim WILQ zaproponuje lokalne działania.",
      source_connectors: ["localo"],
      evidence_ids: ["ev_refresh_refresh_localo_access_ready_test"],
      metric_facts: [],
      action_ids: [],
      blocked_claims: [
        "lokalne rankingi",
        "wyniki profilu firmy w Google",
        "widoczności konkurencji",
        "poprawa widoczności lokalnej"
      ],
      blocked_claim_labels: [
        "lokalne rankingi",
        "wyniki profilu firmy w Google",
        "widoczności konkurencji",
        "poprawa widoczności lokalnej"
      ],
      risk: "medium"
    }
  ],
  evidence_ids: ["ev_refresh_refresh_localo_access_ready_test"],
  action_ids: [],
  blocker_count: 1
};

const ahrefsDiagnostics = {
  generated_at: "2026-06-17T10:00:00Z",
  language: "pl-PL",
  strict_instruction: "WILQ pokazuje tylko metryki z danych źródłowych.",
  connector: {
    id: "ahrefs",
    label: "Ahrefs",
    status: "configured",
    configured: true,
    missing_credentials: [],
    available_credential_sources: ["repo_env"],
    freshness: { state: "fresh" },
    supported_actions: ["content_gap", "backlink_gap", "competitor_gap"]
  },
  connector_status_label: "dostęp skonfigurowany",
  latest_refresh: {
    id: "refresh_ahrefs_test",
    connector_id: "ahrefs",
    mode: "vendor_read",
    status: "completed",
    started_at: "2026-06-17T10:00:00Z",
    completed_at: "2026-06-17T10:00:01Z",
    evidence_ids: ["ev_refresh_refresh_ahrefs_test"],
    missing_credentials: [],
    checked_credentials: ["AHREFS_API_TOKEN"],
    external_call_attempted: true,
    vendor_data_collected: true,
    metric_summary: {
      api: "ahrefs_site_explorer_domain_rating",
      domain_rating: 90,
      ahrefs_rank: 1450
    },
    summary: "Ahrefs domain-rating read completed.",
    errors: [],
    redacted: true
  },
  latest_refresh_status_label: "zakończony",
  live_data_status_label: "metryki Ahrefs dostępne",
  live_data_available: true,
  authority_fact_count: 2,
  gap_fact_count: 0,
  gap_read_contract: {
    id: "ahrefs_gap_read_contract",
    status: "ready",
    status_label: "gotowe",
    title: "Luki SEO z Ahrefs",
    summary: "WILQ ma 2 rekordów luk z Ahrefs. Brakujące dane: brak.",
    available_read_contracts: [
      "ahrefs_authority_summary",
      "ahrefs_gap_metric_facts",
      "ahrefs_competitor_pages",
      "ahrefs_content_gap_records",
      "ahrefs_backlink_gap_records",
      "ahrefs_organic_keywords_by_url",
      "ahrefs_top_pages_by_competitor"
    ],
    available_read_contract_labels: [
      "podsumowanie autorytetu domeny",
      "metryki luk z Ahrefs",
      "strony konkurencji",
      "rekordy luk treści",
      "rekordy luk linków",
      "organiczne słowa per URL",
      "najlepsze strony konkurencji"
    ],
    missing_read_contracts: [],
    missing_read_contract_labels: [],
    allowed_evidence: [
      "domain_rating",
      "ahrefs_rank",
      "ahrefs_content_gap_count",
      "ahrefs_referring_domain_gap_count"
    ],
    allowed_evidence_labels: [
      "ocena domeny Ahrefs",
      "pozycja w rankingu Ahrefs",
      "luki treści",
      "luki domen linkujących"
    ],
    blocked_claims: ["wzrost ruchu", "wzrost autorytetu"],
    blocked_claim_labels: ["wzrost ruchu", "wzrost autorytetu"],
    operator_review_gates: [
      "ahrefs_gap_records_required",
      "content_planner_review_required",
      "human_strategy_review"
    ],
    operator_review_gate_labels: [
      "wymagane konkretne rekordy luk Ahrefs",
      "sprawdzenie w planowaniu treści",
      "sprawdzenie strategii przez człowieka"
    ],
    source_connectors: ["ahrefs"],
    evidence_ids: ["ev_refresh_refresh_ahrefs_test"],
    gap_records: [
      {
        id: "ahrefs_gap_content_gap_test",
        gap_type: "content_gap",
        gap_type_label: "luka treści",
        title: "Luka treści: audyt środowiskowy",
        summary:
          "Luka treści: audyt środowiskowy. Dane Ahrefs: content_gaps=1. To jest materiał do sprawdzenia, nie obietnica wzrostu ruchu.",
        source_url: "https://competitor.example/audyt-srodowiskowy",
        target_url: null,
        competitor_domain: "competitor.example",
        keyword: "audyt środowiskowy",
        metric_facts: [
          {
            name: "ahrefs_content_gap_count",
            value: 1,
            period: "ahrefs_content_gap",
            source_connector: "ahrefs",
            evidence_id: "ev_refresh_refresh_ahrefs_test",
            dimensions: {
              competitor_domain: "competitor.example",
              gap_type: "content_gap",
              keyword: "audyt środowiskowy",
              source_url: "https://competitor.example/audyt-srodowiskowy",
              target_domain: "ekologus.pl"
            },
            unit: null
          }
        ],
        metric_fact_labels: {
          ahrefs_content_gap_count: "luki treści"
        },
        evidence_ids: ["ev_refresh_refresh_ahrefs_test"],
        blocked_claims: ["wzrost ruchu", "wzrost autorytetu"],
        next_step:
          "Połącz rekord z GSC i spisem treści WordPress, potem zdecyduj: zachowanie, odświeżenie, scalenie, utworzenie albo blokada.",
        risk: "medium"
      },
      {
        id: "ahrefs_gap_backlink_gap_test",
        gap_type: "backlink_gap",
        gap_type_label: "luka linków",
        title: "Luka backlinków: example.org",
        summary:
          "Luka backlinków: example.org. Dane Ahrefs: referring_domain_gaps=1. To jest materiał do sprawdzenia, nie obietnica wzrostu ruchu.",
        source_url: "example.org",
        target_url: null,
        competitor_domain: "competitor.example",
        keyword: null,
        metric_facts: [
          {
            name: "ahrefs_referring_domain_gap_count",
            value: 1,
            period: "ahrefs_refdomains_gap",
            source_connector: "ahrefs",
            evidence_id: "ev_refresh_refresh_ahrefs_test",
            dimensions: {
              competitor_domain: "competitor.example",
              gap_type: "backlink_gap",
              referring_domain: "example.org",
              target_domain: "ekologus.pl"
            },
            unit: null
          }
        ],
        metric_fact_labels: {
          ahrefs_referring_domain_gap_count: "luki domen linkujących"
        },
        evidence_ids: ["ev_refresh_refresh_ahrefs_test"],
        blocked_claims: ["wzrost ruchu", "wzrost autorytetu"],
        next_step:
          "Sprawdź ręcznie jakość domen/linków i nie planuj link buildingu bez review ryzyka oraz źródła.",
        risk: "medium"
      },
      {
        id: "ahrefs_gap_competitor_denios",
        gap_type: "competitor_page",
        gap_type_label: "strona konkurencji",
        title: "Strona konkurencji: denios.pl",
        summary:
          "Strona konkurencji: denios.pl. Dane Ahrefs: competitor_pages=1. To jest materiał do sprawdzenia, nie obietnica wzrostu ruchu.",
        source_url: null,
        target_url: null,
        competitor_domain: "denios.pl",
        keyword: null,
        metric_facts: [],
        metric_fact_labels: {},
        evidence_ids: ["ev_refresh_refresh_ahrefs_test"],
        blocked_claims: ["wzrost ruchu", "wzrost autorytetu"],
        next_step:
          "Połącz rekord z GSC i spisem treści WordPress, potem zdecyduj: zachowanie, odświeżenie, scalenie, utworzenie albo blokada.",
        risk: "medium"
      },
      {
        id: "ahrefs_gap_competitor_manutan",
        gap_type: "competitor_page",
        gap_type_label: "strona konkurencji",
        title: "Strona konkurencji: manutan.pl",
        summary:
          "Strona konkurencji: manutan.pl. Dane Ahrefs: competitor_pages=1. To jest materiał do sprawdzenia, nie obietnica wzrostu ruchu.",
        source_url: null,
        target_url: null,
        competitor_domain: "manutan.pl",
        keyword: null,
        metric_facts: [],
        metric_fact_labels: {},
        evidence_ids: ["ev_refresh_refresh_ahrefs_test"],
        blocked_claims: ["wzrost ruchu", "wzrost autorytetu"],
        next_step:
          "Połącz rekord z GSC i spisem treści WordPress, potem zdecyduj: zachowanie, odświeżenie, scalenie, utworzenie albo blokada.",
        risk: "medium"
      },
      {
        id: "ahrefs_gap_competitor_promag",
        gap_type: "competitor_page",
        gap_type_label: "strona konkurencji",
        title: "Strona konkurencji: e-promag.pl",
        summary:
          "Strona konkurencji: e-promag.pl. Dane Ahrefs: competitor_pages=1. To jest materiał do sprawdzenia, nie obietnica wzrostu ruchu.",
        source_url: null,
        target_url: null,
        competitor_domain: "e-promag.pl",
        keyword: null,
        metric_facts: [],
        metric_fact_labels: {},
        evidence_ids: ["ev_refresh_refresh_ahrefs_test"],
        blocked_claims: ["wzrost ruchu", "wzrost autorytetu"],
        next_step:
          "Połącz rekord z GSC i spisem treści WordPress, potem zdecyduj: zachowanie, odświeżenie, scalenie, utworzenie albo blokada.",
        risk: "medium"
      },
      {
        id: "ahrefs_gap_competitor_hidden",
        gap_type: "competitor_page",
        gap_type_label: "strona konkurencji",
        title: "Strona konkurencji: hidden-noise.example",
        summary:
          "Strona konkurencji: hidden-noise.example. Dane Ahrefs: competitor_pages=1. To jest materiał do sprawdzenia, nie obietnica wzrostu ruchu.",
        source_url: null,
        target_url: null,
        competitor_domain: "hidden-noise.example",
        keyword: null,
        metric_facts: [],
        metric_fact_labels: {},
        evidence_ids: ["ev_refresh_refresh_ahrefs_test"],
        blocked_claims: ["wzrost ruchu", "wzrost autorytetu"],
        next_step:
          "Połącz rekord z GSC i spisem treści WordPress, potem zdecyduj: zachowanie, odświeżenie, scalenie, utworzenie albo blokada.",
        risk: "medium"
      }
    ],
    gap_record_count: 6,
    next_step: "Połącz luki Ahrefs z GSC/WordPress i przygotuj kolejkę sprawdzenia.",
    risk: "medium"
  },
  operator_summary: {
    id: "ahrefs_operator_summary",
    title: "Co marketer ma wiedzieć o Ahrefs",
    summary:
      "Ten widok pokazuje, czy Ahrefs może wesprzeć decyzje SEO i content. Autorytet domeny może być kontekstem, ale wnioski o lukach treści lub backlinków wymagają konkretnych danych Ahrefs.",
    next_step:
      "Użyj top decyzji Ahrefs jako kontekstu dla /content-planner. Nie twierdź o lukach treści, lukach backlinków ani wzroście widoczności bez konkretnych danych Ahrefs.",
    top_decision_ids: [
      "ahrefs_review_authority_context",
      "ahrefs_review_gap_records"
    ],
    gap_read_status: "ready",
    gap_read_status_label: "gotowe",
    authority_fact_count: 2,
    gap_fact_count: 0,
    available_read_contracts: [
      "ahrefs_authority_summary",
      "ahrefs_gap_metric_facts",
      "ahrefs_competitor_pages",
      "ahrefs_content_gap_records",
      "ahrefs_backlink_gap_records",
      "ahrefs_organic_keywords_by_url",
      "ahrefs_top_pages_by_competitor"
    ],
    available_read_contract_labels: [
      "podsumowanie autorytetu domeny",
      "metryki luk z Ahrefs",
      "strony konkurencji",
      "rekordy luk treści",
      "rekordy luk linków",
      "organiczne słowa per URL",
      "najlepsze strony konkurencji"
    ],
    missing_read_contracts: [],
    missing_read_contract_labels: [],
    source_connectors: ["ahrefs"],
    evidence_ids: ["ev_refresh_refresh_ahrefs_test"],
    action_ids: [],
    blocked_claims: ["wzrost ruchu", "wzrost autorytetu"],
    blocked_claim_labels: ["wzrost ruchu", "wzrost autorytetu"]
  },
  decision_queue: [
    {
      id: "ahrefs_review_authority_context",
      decision_type: "review_authority_context",
      status: "ready",
      status_label: "gotowe",
      decision_type_label: "kontekst autorytetu",
      title: "Użyj Ahrefs tylko jako kontekstu autorytetu",
      summary: "ocena domeny Ahrefs: 90, pozycja w rankingu Ahrefs: 1450",
      rationale:
        "WILQ ma metryki autorytetu Ahrefs z dowodami, więc może dodać kontekst autorytetu do sprawdzenia SEO/content. To nadal nie jest analiza luk.",
      next_step:
        "Połącz ten kontekst z /content-planner i GSC. Nie twierdź, że Ahrefs wykrył lukę treści/backlinków.",
      priority: 25,
      priority_label: "wysoki priorytet",
      metric_tiles: {
        "ocena domeny Ahrefs": 90,
        "pozycja w rankingu Ahrefs": 1450,
        "luki Ahrefs": 2,
        "brakujące dane": 0
      },
      allowed_evidence: ["domain_rating", "ahrefs_rank", "authority_summary"],
      allowed_evidence_labels: [
        "ocena domeny Ahrefs",
        "pozycja w rankingu Ahrefs",
        "podsumowanie autorytetu domeny"
      ],
      missing_read_contracts: [],
      missing_read_contract_labels: [],
      source_connectors: ["ahrefs"],
      evidence_ids: ["ev_refresh_refresh_ahrefs_test"],
      metric_facts: [
        {
          name: "domain_rating",
          value: 90,
          period: "ahrefs_site_explorer",
          source_connector: "ahrefs",
          evidence_id: "ev_refresh_refresh_ahrefs_test",
          dimensions: { contract: "authority_summary" },
          unit: null
        },
        {
          name: "ahrefs_rank",
          value: 1450,
          period: "ahrefs_site_explorer",
          source_connector: "ahrefs",
          evidence_id: "ev_refresh_refresh_ahrefs_test",
          dimensions: { contract: "authority_summary" },
          unit: null
        }
      ],
      metric_fact_labels: {
        domain_rating: "ocena domeny Ahrefs",
        ahrefs_rank: "pozycja w rankingu Ahrefs"
      },
      action_ids: [],
      blocked_claims: [
        "wzrost ruchu",
        "wzrost autorytetu"
      ],
      blocked_claim_labels: [
        "wzrost ruchu",
        "wzrost autorytetu"
      ],
      risk: "low"
    },
    {
      id: "ahrefs_review_gap_records",
      decision_type: "review_gap_records",
      status: "ready",
      status_label: "gotowe",
      decision_type_label: "sprawdzenie luk",
      title: "Przejrzyj rekordy luk Ahrefs",
      summary:
        "WILQ ma 2 rekordów luk z Ahrefs. Brakujące dane: brak.",
      rationale:
        "To są konkretne rekordy z Ahrefs evidence, więc mogą wejść do sprawdzenia SEO/content.",
      next_step:
        "Połącz rekordy z /content-planner, sprawdź duplikaty WordPress i przygotuj zachowanie, odświeżenie, scalenie, utworzenie albo blokadę zamiast obiecywać wzrost.",
      priority: 18,
      priority_label: "wysoki priorytet",
      metric_tiles: {
        "rekordy luk": 2,
        "brakujące dane": 0
      },
      allowed_evidence: [
        "domain_rating",
        "ahrefs_rank",
        "ahrefs_content_gap_count",
        "ahrefs_referring_domain_gap_count"
      ],
      allowed_evidence_labels: [
        "ocena domeny Ahrefs",
        "pozycja w rankingu Ahrefs",
        "luki treści",
        "luki domen linkujących"
      ],
      missing_read_contracts: [],
      missing_read_contract_labels: [],
      source_connectors: ["ahrefs"],
      evidence_ids: ["ev_refresh_refresh_ahrefs_test"],
      metric_facts: [
        {
          name: "ahrefs_content_gap_count",
          value: 1,
          period: "ahrefs_content_gap",
          source_connector: "ahrefs",
          evidence_id: "ev_refresh_refresh_ahrefs_test",
          dimensions: {
            competitor_domain: "competitor.example",
            gap_type: "content_gap",
            keyword: "audyt środowiskowy"
          },
          unit: null
        }
      ],
      metric_fact_labels: {
        ahrefs_content_gap_count: "luki treści"
      },
      action_ids: [],
      blocked_claims: ["wzrost ruchu", "wzrost autorytetu"],
      blocked_claim_labels: ["wzrost ruchu", "wzrost autorytetu"],
      risk: "low"
    }
  ],
  sections: [
    {
      id: "ahrefs_authority_context",
      title: "Ahrefs: kontekst autorytetu",
      status: "ready",
      status_label: "gotowe",
      summary:
        "WILQ ma 2 świeże dane autorytetu z Ahrefs: ocena domeny Ahrefs: 90, pozycja w rankingu Ahrefs: 1450.",
      diagnosis:
        "Metryki autorytetu Ahrefs mogą wspierać priorytety SEO jako kontekst.",
      next_step:
        "Użyj tych danych jako pomocniczego kontekstu przy sprawdzeniu treści i GSC.",
      source_connectors: ["ahrefs"],
      evidence_ids: ["ev_refresh_refresh_ahrefs_test"],
      metric_facts: [],
      metric_fact_labels: {},
      action_ids: [],
      blocked_claims: [],
      blocked_claim_labels: [],
      risk: "low"
    },
    {
      id: "ahrefs_gap_contract",
      title: "Ahrefs: rekordy luk SEO",
      status: "ready",
      status_label: "gotowe",
      summary: "WILQ ma konkretne luki treści i backlinków z Ahrefs.",
      diagnosis: "To jest materiał do sprawdzenia, nie automatyczna obietnica wzrostu.",
      next_step: "Połącz rekordy z GSC i Spis treści WordPress przed decyzją contentową.",
      source_connectors: ["ahrefs"],
      evidence_ids: ["ev_refresh_refresh_ahrefs_test"],
      metric_facts: [],
      metric_fact_labels: {},
      action_ids: [],
      blocked_claims: ["wzrost ruchu", "wzrost autorytetu"],
      blocked_claim_labels: ["wzrost ruchu", "wzrost autorytetu"],
      risk: "low"
    }
  ],
  evidence_ids: [
    "ev_refresh_refresh_ahrefs_test",
    "ev_refresh_ahrefs_gap_records",
    "ev_refresh_ahrefs_safety"
  ],
  action_ids: [],
  blocker_count: 1
};

const demandGenDiagnostics = {
  status: "blocked",
  title: "Demand Gen: brak kampanii do rekomendacji",
  summary:
    "WILQ ocenił 18 kampanii Ads. Kanały w odczycie: PMax: 8, Search: 10. Kampanie Demand Gen/Discovery: 0. WILQ ma dowody Ads i GA4 do oceny ruchu. Odczyty reklam i kreacji Demand Gen są traktowane jako dostępne tylko wtedy, gdy API zwraca je w dostępnych danych. Nadal brakuje danych: jakość stron wejścia według kampanii, ograniczenia przejścia. To blokuje użyteczną rekomendację; nie jest to problem treści polecenia.",
  metric_tiles: {
    "kampanie Ads": 18,
    kanały: 2,
    "kampanie Demand Gen": 0,
    "reklamy Demand Gen": 1,
    "kreacje Demand Gen": 1,
    "strony wejścia Demand Gen": 0,
    braki: 2
  },
  available_read_contracts: [
    "google_ads_campaign_activity",
    "google_ads_budget_context",
    "google_ads_impression_share_context",
    "ga4_landing_source_campaign_quality",
    "demand_gen_readiness_review_action_object",
    "demand_gen_campaign_rows",
    "demand_gen_ad_group_ad_rows",
    "demand_gen_creative_asset_rows"
  ],
  missing_read_contracts: [
    "demand_gen_landing_quality_by_campaign",
    "demand_gen_transition_constraints"
  ],
  available_read_contract_labels: [
    "aktywność kampanii Google Ads",
    "kontekst budżetu Google Ads",
    "udział w wyświetleniach Google Ads",
    "jakość ruchu GA4 dla stron wejścia",
    "akcja sprawdzenia Demand Gen",
    "wiersze kampanii Demand Gen/Discovery",
    "wiersze reklam Demand Gen",
    "wiersze materiałów kreatywnych"
  ],
  missing_read_contract_labels: [
    "jakość stron wejścia według kampanii",
    "ograniczenia przejścia"
  ],
  operator_review_gate_labels: [
    "konkretne dowody Demand Gen",
    "sprawdzenie strategii przez człowieka",
    "potwierdzenie człowieka przed zapisem"
  ],
  campaign_channel_labels: {
    PERFORMANCE_MAX: "PMax",
    SEARCH: "Search"
  },
  blocked_claims: [
    "rekomendacja uruchomienia Demand Gen",
    "gotowość przejścia na Demand Gen",
    "ocena jakości kreacji",
    "ocena skuteczności materiałów kreatywnych",
    "zmiana kampanii",
    "wzrost skuteczności"
  ],
  source_connectors: ["google_ads", "google_analytics_4"],
  evidence_ids: ["ev_refresh_refresh_google_ads_test", "ev_refresh_refresh_ga4_test"],
  action_ids: ["act_review_demand_gen_readiness"],
  operator_review_gates: [
    "demand_gen_specific_evidence_required",
    "human_strategy_review",
    "human_confirm_before_apply"
  ],
  payload_preview: [
    {
      id: "demand_gen_readiness_review",
      preview_contract: "demand_gen_readiness_review_preview_v1",
      operation_type: "DemandGenReadinessReview",
      campaign_rows_evaluated: 18,
      campaign_channel_counts: {
        PERFORMANCE_MAX: 8,
        SEARCH: 10
      },
      demand_gen_campaign_row_count: 0,
      demand_gen_campaign_rows: [],
      demand_gen_ad_group_ad_row_count: 1,
      demand_gen_ad_group_ad_rows: [
        {
          campaign_id: "103",
          campaign_name: "Demand Gen Test",
          campaign_status: "PAUSED",
          advertising_channel_type: "DEMAND_GEN",
          ad_group_id: "203",
          ad_group_name: "DG grupa",
          ad_id: "803",
          ad_type: "DEMAND_GEN_MULTI_ASSET_AD",
          ad_status: "PAUSED",
          final_url_count: 1,
          asset_reference_count: 4,
          evidence_ids: ["ev_refresh_refresh_google_ads_demand_gen"]
        }
      ],
      demand_gen_creative_asset_row_count: 1,
      demand_gen_creative_asset_rows: [
        {
          asset_id: "901",
          asset_type: "DEMAND_GEN_CAROUSEL_CARD",
          field_type: "DEMAND_GEN_CAROUSEL_CARD",
          impressions: 44,
          evidence_ids: ["ev_refresh_refresh_google_ads_demand_gen"]
        }
      ],
      available_read_contracts: [
        "google_ads_campaign_activity",
        "google_ads_budget_context",
        "google_ads_impression_share_context",
        "ga4_landing_source_campaign_quality",
        "demand_gen_readiness_review_action_object",
        "demand_gen_campaign_rows",
        "demand_gen_ad_group_ad_rows",
        "demand_gen_creative_asset_rows"
      ],
      missing_read_contracts: [
        "demand_gen_landing_quality_by_campaign",
        "demand_gen_transition_constraints"
      ],
      available_read_contract_labels: [
        "aktywność kampanii Google Ads",
        "kontekst budżetu Google Ads",
        "udział w wyświetleniach Google Ads",
        "jakość ruchu GA4 dla stron wejścia",
        "akcja sprawdzenia Demand Gen",
        "wiersze kampanii Demand Gen/Discovery",
        "wiersze reklam Demand Gen",
        "wiersze materiałów kreatywnych"
      ],
      missing_read_contract_labels: [
        "jakość stron wejścia według kampanii",
        "ograniczenia przejścia"
      ],
      required_validation: [
        "review_ads_campaign_channel_context",
        "review_ga4_landing_source_campaign_context",
        "review_demand_gen_missing_contracts",
        "human_strategy_review",
        "human_confirm_before_apply"
      ],
      required_validation_labels: [
        "sprawdzenie kanałów kampanii Ads",
        "sprawdzenie GA4: strona wejścia, źródło ruchu i kampania",
        "sprawdzenie brakujących danych Demand Gen",
        "sprawdzenie strategii przez człowieka",
        "potwierdzenie człowieka przed zapisem"
      ],
      blocked_claims: [
        "rekomendacja uruchomienia Demand Gen",
        "gotowość przejścia na Demand Gen",
        "ocena jakości kreacji",
        "ocena skuteczności materiałów kreatywnych",
        "zmiana kampanii",
        "wzrost skuteczności"
      ],
      evidence_ids: ["ev_refresh_refresh_google_ads_test", "ev_refresh_refresh_ga4_test"],
      api_mutation_ready: false,
      apply_allowed: false,
      destructive: false
    }
  ],
  campaign_rows_evaluated: 18,
  campaign_channel_counts: {
    PERFORMANCE_MAX: 8,
    SEARCH: 10
  },
  demand_gen_campaign_rows: [],
  demand_gen_ad_group_ad_rows: [
    {
      campaign_id: "103",
      campaign_name: "Demand Gen Test",
      campaign_status: "PAUSED",
      advertising_channel_type: "DEMAND_GEN",
      ad_group_id: "203",
      ad_group_name: "DG grupa",
      ad_id: "803",
      ad_type: "DEMAND_GEN_MULTI_ASSET_AD",
      ad_status: "PAUSED",
      final_url_count: 1,
      asset_reference_count: 4,
      evidence_ids: ["ev_refresh_refresh_google_ads_demand_gen"]
    }
  ],
  demand_gen_creative_asset_rows: [
    {
      asset_id: "901",
      asset_type: "DEMAND_GEN_CAROUSEL_CARD",
      field_type: "DEMAND_GEN_CAROUSEL_CARD",
      impressions: 44,
      evidence_ids: ["ev_refresh_refresh_google_ads_demand_gen"]
    }
  ],
  next_step:
    "Sprawdź gotowość Demand Gen w WILQ jako akcję tylko do przeglądu. Zanim WILQ pokaże propozycje uruchomienia albo przejścia kampanii, potwierdź dostępność danych o jakości stron wejścia i ograniczeniach przejścia.",
  risk: "medium"
};

const expertRules = [
  {
    id: "ads_search_terms_v1",
    name: "Search term analysis",
    domain: "ads",
    version: 1,
    source_anchor: "Google Ads listy wyszukiwanych haseł",
    source_path: "wilq/expert/ads/search_terms.yaml",
    when_to_use: "Wykrywaj przepalanie budżetu i pomysły na treści z listy wyszukiwanych haseł.",
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
    title: "Diagnostyka wyszukiwanych haseł Google Ads",
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
    title: "Diagnostyka wyszukiwanych haseł Google Ads",
    card_type: "ads_pattern_card",
    source_anchors: ["Google Ads listy wyszukiwanych haseł"],
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

const knowledgeOperatingMap = {
  generated_at: "2026-06-17T10:00:00Z",
  source_card_count: 1,
  playbook_count: 1,
  expert_rule_count: 1,
  binding_count: 1,
  bindings: [
    {
      id: "knowledge_ads_daily_check",
      title: "Ocena Ads",
      status: "ready",
      route: "/ads-doctor",
      skill_id: "wilq-ads-doctor",
      summary: "Google Ads search diagnostics steruje review kampanii i listy wyszukiwanych haseł.",
      next_step: "Otwórz /ads-doctor i użyj wiedzy tylko z evidence.",
      source_connectors: ["google_ads"],
      evidence_ids: ["ev_refresh_refresh_google_ads_test"],
      action_ids: ["act_prepare_ads_campaign_review_queue"],
      metric_tiles: { kampanie: 18, zapytania: 50 },
      knowledge_card_ids: ["card_google_ads_search_playbook"],
      playbook_ids: ["google_ads_search_playbook"],
      expert_rule_ids: ["ads_search_terms_v1"],
      required_evidence: ["search_terms", "evidence_ids"],
      missing_contracts: [],
      blocked_claims: ["ocena zmarnowanego budżetu"],
      source_lineage: ["wilq/knowledge/playbooks/marketing_playbooks.yaml", "ads_search_terms_v1"],
      risk: "low"
    }
  ]
};

function mockFetch() {
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string) => {
      if (url.endsWith("/api/dashboard/command-center")) {
        return Promise.resolve(
          Response.json({
            generated_at: "2026-06-17T10:00:00Z",
            strict_instruction: "WILQ pokazuje tylko metryki z danych źródłowych.",
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
                  "Merchant Center ma produkty=10900, typy problemów=15, zgłoszenia=1887, decyzje=8, blockery=0. To jest kolejka ręcznego review feedu; WILQ nie twierdzi, że zatwierdzenie, przychód albo dane produktu zostały już naprawione.",
                dlaczego_to_ma_znaczenie:
                  "WILQ widzi 10900 produktów i 1887 zgłoszeń problemów feedu. To wymaga ręcznego review przed zmianami.",
                bezpieczny_next_step:
                  "Otwórz /merchant, sprawdź kolejkę problemów i sprawdź propozycję w WILQ.",
                why_it_matters:
                  "WILQ widzi 10900 produktów i 1887 zgłoszeń problemów feedu. To wymaga ręcznego review przed zmianami.",
                operator_action:
                  "Otwórz /merchant, sprawdź kolejkę problemów i sprawdź propozycję w WILQ.",
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
                blocked_claims: ["ponowne zatwierdzenie produktu", "automatyczna zmiana feedu"],
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
                  "GSC i WordPress tworzą kolejkę SEO: query/page=1, WP match=1, decyzje=1, wyświetlenia=120, kliknięcia=12. To jest decyzja odświeżenia, scalenia, nowej treści albo blokady oparta o query/page i spisie treści, nie obietnica leadów ani wzrostów pozycji.",
                dlaczego_to_ma_znaczenie:
                  'GSC: 120 wyświetleń, 12 kliknięć, CTR 10.00%; główne zapytanie: "bdo". WordPress potwierdza istniejącą stronę, więc to jest decyzja odświeżenia albo scalenia, nie nowy artykuł. Pełny widok query/page i URL jest w /content-planner.',
                bezpieczny_next_step:
                  'Otwórz /content-planner i zacznij od: SEO: odśwież lub scal "bdo" (1 zapytanie).',
                why_it_matters:
                  'GSC: 120 wyświetleń, 12 kliknięć, CTR 10.00%; główne zapytanie: "bdo". WordPress potwierdza istniejącą stronę, więc to jest decyzja odświeżenia albo scalenia, nie nowy artykuł. Pełny widok query/page i URL jest w /content-planner.',
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
                blocked_claims: ["wzrost liczby leadów", "gwarancja pozycji"],
                risk: "low"
              },
              {
                id: "decision_review_ads_campaign_metrics",
                title: "Przejrzyj kampanie Google Ads z live metryk",
                route: "/ads-doctor",
                status: "ready",
                priority: 16,
                metric_tiles: { kampanie: 18, "listy wyszukiwanych haseł": 50 },
                co_widzimy:
                  "Google Ads ma kolejki do oceny: kampanie=18, listy wyszukiwanych haseł=50. To są kolejki budżetu, rekomendacji, wykluczeń i segmentów. Zapis zmian, ocena rentowności i werdykty o przepalonym budżecie pozostają zablokowane.",
                dlaczego_to_ma_znaczenie:
                  "Google Ads OAuth, MCC login i child customer działają.",
                bezpieczny_next_step:
                  "Otwórz /ads-doctor i analizuj tylko metryki widoczne w evidence.",
                why_it_matters:
                  "Google Ads OAuth, MCC login i child customer działają.",
                operator_action:
                  "Otwórz /ads-doctor i analizuj tylko metryki widoczne w evidence.",
                source_connectors: ["google_ads"],
                evidence_ids: ["ev_refresh_refresh_google_ads_test"],
                action_ids: [],
                blocked_claims: ["koszt pozyskania celu", "zwrot z reklam", "marnowanie budżetu na zapytaniach"],
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
                summary: "Google Ads ma live metryki.",
                next_step: "Otwórz /ads-doctor i przejdź do przeglądu wyników.",
                source_connectors: ["google_ads"],
                evidence_ids: ["ev_refresh_refresh_google_ads_test"],
                action_ids: [],
                metric_tiles: { kampanie: 18, "listy wyszukiwanych haseł": 50, blockery: 1 },
                blocked_claims: ["koszt pozyskania celu", "zwrot z reklam", "marnowanie budżetu na zapytaniach"],
                risk: "medium"
              },
              {
                id: "daily_merchant_feed",
                title: "Merchant: kolejka problemów feedu",
                route: "/merchant",
                status: "ready",
                priority: 10,
                summary:
                  "Produkty=10900, typy problemów=15, zgłoszenia=1887, decyzje=8. To jest kolejka do sprawdzenia.",
                next_step:
                  "Otwórz /merchant i przejrzyj decyzje feedu przed sprawdzeniem propozycji w WILQ.",
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
                blocked_claims: ["ponowne zatwierdzenie produktu", "automatyczna zmiana feedu"],
                risk: "medium"
              },
              {
                id: "daily_content_queue",
                title: "Content: kolejka SEO z GSC i WordPress",
                route: "/content-planner",
                status: "ready",
                priority: 12,
                summary:
                  'GSC: 120 wyświetleń, 12 kliknięć, CTR 10.00%; główne zapytanie: "bdo". WordPress potwierdza istniejącą stronę, więc to jest decyzja odświeżenia albo scalenia, nie nowy artykuł.',
                next_step:
                  'Otwórz /content-planner i zacznij od: SEO: odśwież lub scal "bdo" (1 zapytanie).',
                source_connectors: ["google_search_console", "wordpress_ekologus"],
                evidence_ids: ["ev_refresh_gsc", "ev_refresh_wordpress_inventory"],
                action_ids: ["act_prepare_content_refresh_queue"],
                metric_tiles: { "query/page": 1, "WP match": 1, decyzje: 1, wyświetlenia: 120, kliknięcia: 12 },
                blocked_claims: ["wzrost liczby leadów", "gwarancja pozycji"],
                risk: "low"
              },
              {
                id: "daily_ga4_landing_quality",
                title: "GA4: pomiar i jakość ruchu do kontroli",
                route: "/ga4",
                status: "blocked",
                priority: 14,
                summary:
                  "GA4 ma 1 grupę stron wejścia, źródeł ruchu i kampanii i 1 decyzję do kontroli: pomiar=1, jakość ruchu=0. Blokada oznacza brak danych do wniosków o zwrocie z reklam, przychodzie, spadku konwersji i naprawionym pomiarze; to nie jest awaria źródła danych.",
                next_step:
                  "Otwórz /ga4 i przejdź przez kolejkę decyzji. Sprawdź jakość pomiaru w WILQ.",
                source_connectors: ["google_analytics_4"],
                evidence_ids: ["ev_refresh_ga4"],
                action_ids: ["act_review_ga4_tracking_quality"],
                metric_tiles: {
                  "grupy ruchu": 1,
                  decyzje: 1,
                  pomiar: 1,
                  "jakość ruchu": 0,
                  "brakujące dane": 1
                },
                blocked_claims: ["zwrot z reklam", "przychód", "spadek konwersji", "naprawiony pomiar"],
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
                  "WILQ zbiera gotowe źródła, blockery, evidence IDs i akcje do sprawdzenia.",
                operator_prompt: "Pokaż dzisiejszy priorytet i akcje do sprawdzenia.",
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
                  "Merchant Center daje realne metryki product/feed i przegląd akcji.",
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
                  "Otwórz /merchant, sprawdź kolejkę problemów i sprawdź propozycję w WILQ.",
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
                blocked_claims: ["ponowne zatwierdzenie produktu", "automatyczna zmiana feedu"],
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
                  'GSC: 120 wyświetleń, 12 kliknięć, CTR 10.00%; główne zapytanie: "bdo". WordPress potwierdza istniejącą stronę, więc to jest decyzja odświeżenia albo scalenia, nie nowy artykuł. Pełny widok query/page i URL jest w /content-planner.',
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
                blocked_claims: ["wzrost liczby leadów", "gwarancja pozycji"],
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
                blocked_claims: ["koszt pozyskania celu", "zwrot z reklam", "marnowanie budżetu na zapytaniach"],
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
      if (url.includes("/api/ads/diagnostics")) {
        return Promise.resolve(Response.json(adsDiagnostics));
      }
      if (url.endsWith("/api/merchant/diagnostics")) {
        return Promise.resolve(Response.json(merchantDiagnostics));
      }
      if (url.endsWith("/api/content/diagnostics")) {
        return Promise.resolve(Response.json(contentDiagnostics));
      }
      if (url.endsWith("/api/content/preflight")) {
        return Promise.resolve(Response.json(contentPreflight));
      }
      if (url.endsWith("/api/ga4/diagnostics")) {
        return Promise.resolve(Response.json(ga4Diagnostics));
      }
      if (url.endsWith("/api/localo/diagnostics")) {
        return Promise.resolve(Response.json(localoDiagnostics));
      }
      if (url.endsWith("/api/ahrefs/diagnostics")) {
        return Promise.resolve(Response.json(ahrefsDiagnostics));
      }
      if (url.endsWith("/api/demand-gen/diagnostics")) {
        return Promise.resolve(Response.json(demandGenDiagnostics));
      }
      if (url.endsWith("/api/connectors")) return Promise.resolve(Response.json(connectors));
      if (url.includes("/api/metrics?")) return Promise.resolve(Response.json(metricFacts));
      if (url.endsWith("/api/metrics/status")) return Promise.resolve(Response.json(metricStoreStatus));
      if (url.endsWith("/api/opportunities")) return Promise.resolve(Response.json(opportunities));
      if (url.endsWith("/api/actions")) return Promise.resolve(Response.json(actions));
      if (url.includes("/api/actions/")) {
        const actionPath = url.split("/api/actions/")[1] ?? "";
        if (!actionPath.includes("/")) {
          const action = actions.find((item) => item.id === actionPath);
          return action
            ? Promise.resolve(Response.json(action))
            : Promise.resolve(Response.json({ detail: "Unknown action" }, { status: 404 }));
        }
      }
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
      if (url.includes("/api/actions/") && url.endsWith("/review")) {
        const actionId = url.split("/api/actions/")[1]?.replace("/review", "") ?? "unknown";
        return Promise.resolve(
          Response.json({
            action_id: actionId,
            status: "recorded",
            audit_event: {
              id: `audit_${actionId}_human_review_test`,
              action_id: actionId,
              event_type: "human_review_approved_for_prepare",
              actor: "operator_local_dashboard",
              created_at: "2026-06-17T10:00:00Z",
              summary: "Wynik review: zatwierdzone do dalszego przygotowania.",
              evidence_ids: ["ev_refresh_merchant_feed"],
              redacted: true
            },
            review_gate: {
              status: "pending_validation",
              summary: "Wymaga sprawdzenia w WILQ przed kolejnym krokiem.",
              required_checks: [],
              operator_checklist: [],
              apply_blockers: ["action_validation_required"],
              confirmation_required: true,
              apply_allowed: false,
              last_review_outcome: "approved_for_prepare",
              last_reviewed_by: "operator_local_dashboard",
              last_reviewed_at: "2026-06-17T10:00:00Z",
              last_review_summary: "Wynik review: zatwierdzone do dalszego przygotowania."
            }
          })
        );
      }
      if (url.includes("/api/actions/") && url.endsWith("/preview")) {
        const actionId = url.split("/api/actions/")[1]?.replace("/preview", "") ?? "unknown";
        return Promise.resolve(
          Response.json({
            action_id: actionId,
            status: "blocked",
            dry_run: true,
            mutation_allowed: false,
            preview_contract: "merchant_feed_issue_preview_v1",
            preview_items: [],
            preview_items_total: 0,
            omitted_items: 0,
            blockers: ["payload_preview_missing", "action_validation_required"],
            blocker_labels: ["brak pozycji do pokazania w podglądzie", "wymagane sprawdzenie w WILQ"],
            audit_event: {
              id: `audit_${actionId}_preview_test`,
              action_id: actionId,
              event_type: "action_preview_generated",
              actor: "operator_local_dashboard",
              created_at: "2026-06-17T10:00:00Z",
              summary: "Podgląd zmian wygenerowany bez zmian w zewnętrznych systemach.",
              evidence_ids: ["ev_refresh_merchant_feed"],
              redacted: true
            },
            review_gate: {
              status: "pending_validation",
              summary: "Wymaga sprawdzenia w WILQ przed kolejnym krokiem.",
              required_checks: [],
              operator_checklist: [],
              apply_blockers: ["action_validation_required"],
              confirmation_required: true,
              apply_allowed: false
            }
          })
        );
      }
      if (url.includes("/api/actions/") && url.endsWith("/confirm")) {
        const actionId = url.split("/api/actions/")[1]?.replace("/confirm", "") ?? "unknown";
        return Promise.resolve(
          Response.json({
            action_id: actionId,
            confirmed: true,
            status: "confirmed",
            blockers: [],
            blocker_labels: [],
            audit_event: {
              id: `audit_${actionId}_confirm_test`,
              action_id: actionId,
              event_type: "action_apply_confirmed",
              actor: "operator_local_dashboard",
              created_at: "2026-06-17T10:01:00Z",
              summary: "Potwierdzenie preview zapisane bez vendor mutations.",
              evidence_ids: ["ev_refresh_merchant_feed"],
              redacted: true
            },
            review_gate: {
              status: "pending_validation",
              summary: "Wymaga sprawdzenia w WILQ przed kolejnym krokiem.",
              required_checks: [],
              operator_checklist: [],
              apply_blockers: ["action_validation_required"],
              confirmation_required: true,
              apply_allowed: false,
              last_confirmation_by: "operator_local_dashboard",
              last_confirmation_at: "2026-06-17T10:01:00Z",
              last_confirmation_summary: "Potwierdzenie preview zapisane bez vendor mutations."
            }
          })
        );
      }
      if (url.includes("/api/actions/") && url.endsWith("/impact-check")) {
        const actionId = url.split("/api/actions/")[1]?.replace("/impact-check", "") ?? "unknown";
        return Promise.resolve(
          Response.json({
            action_id: actionId,
            status: "checked",
            pre_window_days: 7,
            post_window_days: 7,
            metric_fact_count: 2,
            source_connectors: ["google_merchant_center"],
            evidence_ids: ["ev_refresh_merchant_feed"],
            blockers: [],
            blocker_labels: [],
            audit_event: {
              id: `audit_${actionId}_impact_test`,
              action_id: actionId,
              event_type: "action_impact_check_completed",
              actor: "operator_local_dashboard",
              created_at: "2026-06-17T10:02:00Z",
              summary: "Sprawdzenie efektu completed without vendor mutations.",
              evidence_ids: ["ev_refresh_merchant_feed"],
              redacted: true
            },
            review_gate: {
              status: "pending_validation",
              summary: "Wymaga sprawdzenia w WILQ przed kolejnym krokiem.",
              required_checks: [],
              operator_checklist: [],
              apply_blockers: ["action_validation_required"],
              confirmation_required: true,
              apply_allowed: false,
              last_impact_check_status: "checked",
              last_impact_checked_by: "operator_local_dashboard",
              last_impact_checked_at: "2026-06-17T10:02:00Z",
              last_impact_check_summary: "Sprawdzenie efektu completed without vendor mutations."
            }
          })
        );
      }
      if (url.includes("/api/evidence/")) {
        const evidenceId = decodeURIComponent(url.split("/api/evidence/")[1] ?? "");
        const evidenceItem = evidence.find((item) => item.id === evidenceId);
        if (evidenceItem) return Promise.resolve(Response.json(evidenceItem));
        return Promise.resolve(Response.json({ detail: "Evidence not found" }, { status: 404 }));
      }
      if (url.endsWith("/api/evidence")) return Promise.resolve(Response.json(evidence));
      if (url.endsWith("/api/connectors/refresh-runs")) {
        return Promise.resolve(Response.json(connectorRefreshRuns));
      }
      if (url.endsWith("/api/expert/rules")) return Promise.resolve(Response.json(expertRules));
      if (url.endsWith("/api/workflows")) {
        return Promise.resolve(
          Response.json([
            {
              id: "daily_command",
              label: "Plan dnia WILQ",
              description: "Główny proces pracy oparty o WILQ.",
              steps: [
                {
                  id: "daily_command_context",
                  label: "Pobierz kontekst z WILQ",
                  required_connectors: ["google_ads"],
                  output_contract: "Daily decisions and action IDs."
                }
              ],
              status: "ready",
              status_label: "gotowe",
              route: "/command-center",
              route_label: "Plan dnia",
              skill_id: "wilq-daily-command",
              safe_next_step: "Otwórz Command Center i przejdź decyzje według priorytetu.",
              source_connectors: ["google_ads"],
              evidence_ids: ["ev_refresh_refresh_google_ads_test"],
              action_ids: ["act_prepare_ads_campaign_review_queue"],
              blocked_claims: ["ocena zwrotu z reklam"],
              metric_tiles: { decyzje: 4, blockery: 0, źródła: 1, akcje: 1 },
              missing_contracts: [],
              risk: "low",
              risk_label: "niskie ryzyko"
            },
            {
              id: "localo_visibility_review",
              label: "Widoczność lokalna Localo",
              description: "Planowany proces lokalnej widoczności.",
              steps: [],
              status: "blocked",
              status_label: "zablokowane",
              route: "/localo",
              route_label: "Localo",
              skill_id: "wilq-localo-operator",
              safe_next_step: "Otwórz widok Localo i potraktuj proces jako zablokowany.",
              source_connectors: ["localo"],
              evidence_ids: [],
              action_ids: [],
              blocked_claims: ["poprawa lokalnych rankingów"],
              metric_tiles: {},
              missing_contracts: ["local_ranking_rows"],
              risk: "medium",
              risk_label: "średnie ryzyko"
            }
          ])
        );
      }
      if (url.endsWith("/api/workflow-runs")) return Promise.resolve(Response.json(workflowRuns));
      if (url.endsWith("/api/knowledge/cards")) return Promise.resolve(Response.json(knowledgeCards));
      if (url.endsWith("/api/knowledge/operating-map")) {
        return Promise.resolve(Response.json(knowledgeOperatingMap));
      }
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

  it("connector status renders", async () => {
    renderApp("/settings");
    await waitFor(() => expect(screen.getByText("Google Ads")).toBeInTheDocument());
    expect(screen.getByRole("heading", { name: "Ustawienia" })).toBeInTheDocument();
    expect(screen.getByText("Braki dostępu")).toBeInTheDocument();
    expect(screen.getByText(/Brakuje dostępu do Google Ads/)).toBeInTheDocument();
    expect(screen.queryByText(/GOOGLE_ADS_DEVELOPER_TOKEN/)).not.toBeInTheDocument();
    expect(screen.queryByText("google_ads")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Pokaż stan dostępu" })).toBeInTheDocument();
    expect(screen.queryByText("Missing credentials")).not.toBeInTheDocument();
    expect(screen.queryByText("Configured")).not.toBeInTheDocument();
    expect(screen.queryByText(/Source:/)).not.toBeInTheDocument();
    expect(screen.queryByText("Evidence Registry")).not.toBeInTheDocument();
    expect(screen.queryByText("Connector Refresh Runs")).not.toBeInTheDocument();
    expect(screen.queryByText("Expert Rules")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Pokaż stan dostępu" }));
    expect(screen.getAllByText("Google Ads").length).toBeGreaterThan(0);
    expect(screen.getByText("Źródło danych sprawdzane przez WILQ.")).toBeInTheDocument();
    expect(screen.getByText("Brakujące ustawienia dostępu")).toBeInTheDocument();
    expect(screen.getByText("1 pole")).toBeInTheDocument();
    expect(screen.queryByText(/GOOGLE_ADS_DEVELOPER_TOKEN/)).not.toBeInTheDocument();
    expect(screen.queryByText("google_ads")).not.toBeInTheDocument();
  });

  it("secondary utility routes render compact blockers instead of generic registries", async () => {
    renderApp("/google-sheets");
    await waitFor(() => expect(screen.getByRole("heading", { name: "Google Sheets" })).toBeInTheDocument());
    expect(screen.getByText("Status widoku")).toBeInTheDocument();
    expect(screen.getByText(/brak zatwierdzonego zakresu eksportu/i)).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "OPPORTUNITIES" })).not.toBeInTheDocument();
    expect(screen.queryByText("Connector Refresh Runs")).not.toBeInTheDocument();
    expect(screen.queryByText(/GOOGLE_ADS \/ PREPARE/)).not.toBeInTheDocument();
    expect(screen.queryByText(/vendor_read/)).not.toBeInTheDocument();

    cleanup();

    renderApp("/security");
    await waitFor(() => expect(screen.getByRole("heading", { name: "Bezpieczeństwo" })).toBeInTheDocument());
    expect(screen.getByText("Status widoku")).toBeInTheDocument();
    expect(screen.getByText(/brak pełnego dashboardu bezpieczeństwa/i)).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "OPPORTUNITIES" })).not.toBeInTheDocument();
    expect(screen.queryByText("Evidence Registry")).not.toBeInTheDocument();
    expect(screen.queryByText(/CONNECTOR_REFRESH_RUN/)).not.toBeInTheDocument();
  });

  it("actions route starts from marketer-facing actions instead of registry dumps", async () => {
    renderApp("/actions");
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "Akcje do sprawdzenia" })).toBeInTheDocument()
    );
    expect(screen.getByText("Najważniejsze na start")).toBeInTheDocument();
    expect(screen.getByText("Pozostałe akcje")).toBeInTheDocument();
    expect(screen.getByText(/Zacznij od sprawdzeń, które odpowiadają core path/i)).toBeInTheDocument();
    expect(screen.getByText("Przygotuj kolejkę przeglądu feedu Merchant Center")).toBeInTheDocument();
    expect(screen.getByText("Przygotuj kolejkę odświeżenia treści ekologus.pl")).toBeInTheDocument();
    expect(screen.getByText("Sprawdź jakość pomiaru GA4 przed oceną kampanii")).toBeInTheDocument();
    expect(screen.queryByText("Dowody powiązane z akcjami")).not.toBeInTheDocument();
    expect(screen.getByText("Do sprawdzenia")).toBeInTheDocument();
    expect(screen.queryByText("Najważniejsze akcje demo")).not.toBeInTheDocument();
    expect(screen.queryByText("Pełna lista akcji - szczegóły")).not.toBeInTheDocument();
    expect(screen.queryByText(/GOOGLE_ADS \/ PREPARE/)).not.toBeInTheDocument();
    expect(screen.queryByText("Odnow Google Ads OAuth refresh token")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Pokaż pozostałe akcje/ })).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Otwórz akcję" }).length).toBeGreaterThan(0);
    expect(screen.queryByRole("button", { name: "Pokaż dane techniczne akcji" })).not.toBeInTheDocument();
    expect(screen.queryByText(/"action_type"/)).not.toBeInTheDocument();
    expect(screen.getAllByText("Dowody: 1 ID").length).toBeGreaterThan(0);
    expect(screen.queryByText("ev_1")).not.toBeInTheDocument();
    expect(screen.queryByText("ev_connector_google_ads_status")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "OPPORTUNITIES" })).not.toBeInTheDocument();
    expect(screen.queryByText("Connector Refresh Runs")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Pokaż pozostałe akcje/ }));
    expect(
      screen.getAllByText("Otwórz akcję, żeby sprawdzić warunki i bezpieczny zapis zmian.").length
    ).toBeGreaterThan(0);
    expect(screen.queryByText(/GOOGLE_ADS \/ PREPARE/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Pokaż dane techniczne akcji" })).not.toBeInTheDocument();
    expect(screen.queryByText(/"action_type"/)).not.toBeInTheDocument();
  });

  it("connector refresh run cards summarize evidence instead of printing raw IDs", () => {
    render(
      <ConnectorRefreshRunList
        runs={[
          {
            ...connectorRefreshRuns[0],
            metric_summary: {
              clicks: 12,
              impressions: 120,
              api: "google_ads_probe"
            }
          }
        ]}
      />
    );

    expect(screen.getByText("Dowody: 2 ID")).toBeInTheDocument();
    expect(screen.getByText("Metryki: 3 wartości")).toBeInTheDocument();
    expect(screen.queryByText("ev_connector_google_ads_status")).not.toBeInTheDocument();
    expect(screen.queryByText("ev_refresh_refresh_google_ads_test")).not.toBeInTheDocument();
    expect(screen.queryByText("vendor_read")).not.toBeInTheDocument();
    expect(screen.queryByText(/"clicks"/)).not.toBeInTheDocument();
  });

  it("ads doctor route renders live metric-backed diagnostics", async () => {
    renderApp("/ads-doctor");
    expect(
      await screen.findByRole("heading", { name: "Ads Doctor" }, { timeout: 5000 })
    ).toBeInTheDocument();
    expect(screen.getByText("Decyzja skondensowana")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Aktualny odczyt Ads" })).toBeInTheDocument();
    expect(screen.getByText("Wartości Ads")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Pełny przegląd Ads" })).toBeInTheDocument();
    expect(screen.queryByText("google_ads")).not.toBeInTheDocument();
    expect(screen.queryByText("google_analytics_4")).not.toBeInTheDocument();
    expect(screen.queryByText("wordpress_ekologus")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Co marketer ma sprawdzić teraz w Google Ads" })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Co można zrobić teraz w Ads" })
    ).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Pokaż pełny przegląd Ads" }));
    expect(
      await screen.findByRole(
        "heading",
        { name: "Co marketer ma sprawdzić teraz w Google Ads" },
        { timeout: 5000 }
      )
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Co można zrobić teraz w Ads" })
    ).toBeInTheDocument();
    expect(screen.queryByText("google_ads")).not.toBeInTheDocument();
    expect(screen.queryByText("google_analytics_4")).not.toBeInTheDocument();
    expect(screen.queryByText("wordpress_ekologus")).not.toBeInTheDocument();
    const optimizerPanel = screen
      .getByRole("heading", { name: "Co można zrobić teraz w Ads" })
      .closest(".mb-4");
    expect(optimizerPanel).not.toBeNull();
    expect(within(optimizerPanel as HTMLElement).queryByText(/ev_/)).not.toBeInTheDocument();
    expect(
      within(optimizerPanel as HTMLElement).queryByText(/act_(prepare|review|configure|apply)/)
    ).not.toBeInTheDocument();
    const safeModePanel = screen
      .getByRole("heading", { name: "Bezpieczny tryb Ads" })
      .closest(".rounded-md");
    expect(safeModePanel).not.toBeNull();
    expect(within(safeModePanel as HTMLElement).queryByText(/ev_/)).not.toBeInTheDocument();
    expect(
      within(safeModePanel as HTMLElement).queryByText(/act_(prepare|review|configure|apply)/)
    ).not.toBeInTheDocument();
    const campaignReviewDecision = screen
      .getByRole("heading", { name: "Ustal kolejność oceny kampanii Ads" })
      .closest("article");
    expect(campaignReviewDecision).not.toBeNull();
    expect(
      within(campaignReviewDecision as HTMLElement).queryByText(/ev_/)
    ).not.toBeInTheDocument();
    expect(
      within(campaignReviewDecision as HTMLElement).queryByText(/act_(prepare|review|configure|apply)/)
    ).not.toBeInTheDocument();
    expect(screen.getByText("kampanie do oceny")).toBeInTheDocument();
    expect(screen.getByText("historia zmian")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Gotowość oceny wpływu zmian" })
    ).toBeInTheDocument();
    expect(screen.getAllByText("odczyt kampanii").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/bieżące kliknięcia kampanii/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/okno wyników przed zmianą/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/okno wyników po zmianie/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/wpływ zmian/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/zmiana kampanii/).length).toBeGreaterThan(0);
    expect(screen.getByText("Przejrzyj aktywność kampanii Google Ads")).toBeInTheDocument();
    expect(
      screen.getByText("Przejrzyj zapytania z reklam bez automatycznych wykluczeń")
    ).toBeInTheDocument();
    expect(
      screen.getByText("Przejrzyj rekomendacje Google Ads bez zapisu zmian")
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Nie zapisuj wykluczeń, budżetów ani rekomendacji/)
    ).toBeInTheDocument();
    expect(screen.queryByText("Handoff blockera Ads")).not.toBeInTheDocument();
    expect(screen.queryByText(/handoff blockera OAuth/i)).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Dowody i ograniczenia Ads" })).toBeInTheDocument();
    expect(screen.getAllByText("Ekologus Search").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Konwersje").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Wartość konwersji").length).toBeGreaterThan(0);
    expect(screen.getAllByText("450,75").length).toBeGreaterThan(0);
    expect(screen.getAllByText("kliknięcia").length).toBeGreaterThan(0);
    expect(screen.getAllByText("wyświetlenia").length).toBeGreaterThan(0);
    expect(screen.getAllByText("koszt").length).toBeGreaterThan(0);
    expect(screen.getAllByText("164.6").length).toBeGreaterThan(0);
    expect(screen.getAllByText("podgląd wpływu").length).toBeGreaterThan(0);
    expect(screen.queryByText("Koszt 7 dni")).not.toBeInTheDocument();
    expect(screen.queryByText("7-dniowy budżet")).not.toBeInTheDocument();
    expect(screen.getAllByText("78,38%").length).toBeGreaterThan(0);
    expect(
      screen.getAllByRole("heading", { name: "Kolejność oceny kampanii" }).length
    ).toBeGreaterThan(0);
    expect(screen.queryByRole("heading", { name: "Podział wspólnych budżetów" })).not.toBeInTheDocument();
    expect(screen.queryByText("Ekologus Generic Search")).not.toBeInTheDocument();
    expect(screen.queryByText(/72,91%/)).not.toBeInTheDocument();
    expect(screen.queryByText("CAMPAIGN_BUDGET")).not.toBeInTheDocument();
    expect(screen.queryByText(/SEARCH \/ ENABLED/)).not.toBeInTheDocument();
    expect(screen.getAllByText(/automatyczne przyjęcie rekomendacji/).length).toBeGreaterThan(0);
    expect(screen.queryByText(/Karty wiedzy:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/card_google_ads_budget_review_playbook/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Reguły:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/ads_scaling_candidates_v1/)).not.toBeInTheDocument();
    expect(screen.queryByText(/wartość_konwersji=120/)).not.toBeInTheDocument();
    expect(screen.getAllByText(/Brakujące dane/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Wymagana ocena/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/ocena strategii przez człowieka/).length).toBeGreaterThan(0);
    expect(
      screen.getByRole("heading", { name: "Gotowość oceny strategii Ads" })
    ).toBeInTheDocument();
    expect(screen.getAllByText("brak oceny").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/ocena wskaźników względem celu/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Hasła źródłowe:.*bdo rejestracja/).length).toBeGreaterThan(0);
    expect(screen.queryByText(/Source terms:/)).not.toBeInTheDocument();
    expect(screen.getAllByText(/90-dniowa kontrola bezpieczeństwa/).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Pokaż pełne tabele diagnostyczne" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Podział wspólnych budżetów" })).not.toBeInTheDocument();
    expect(screen.queryByText("Odnow Google Ads OAuth refresh token")).not.toBeInTheDocument();
    expect(screen.queryByText(/zmarnowany koszt/)).not.toBeInTheDocument();
    expect(screen.queryByText("Read contract Ads")).not.toBeInTheDocument();
    expect(screen.queryByText("Search terms read-only")).not.toBeInTheDocument();
    expect(screen.queryByText("Campaign activity read contract")).not.toBeInTheDocument();
    expect(screen.queryByText("Evidence")).not.toBeInTheDocument();
    expect(screen.queryByText("configured")).not.toBeInTheDocument();
    const routeSource = readFileSync("src/routes/AdsDoctorSurface.tsx", "utf8");
    expect(routeSource).toContain("summary.missing_read_contract_labels");
    expect(routeSource).toContain("summary.blocked_claim_labels");
    expect(routeSource).toContain("optimizer_readiness_contract");
    expect(routeSource).toContain("contract.mode_label");
    expect(routeSource).toContain("item.missing_read_contract_labels");
    expect(routeSource).toContain("interpretation.allowed_use_labels");
    expect(routeSource).toContain("interpretation.blocked_use_labels");
    expect(routeSource).toContain("interpretation.missing_requirement_labels");
    expect(routeSource).toContain("interpretation.status_label");
    expect(routeSource).toContain("strategyReadiness.status_label");
    expect(routeSource).toContain("strategyReadiness.latest_review_status_label");
    expect(routeSource).toContain("strategyReadiness.missing_read_contract_labels");
    expect(routeSource).toContain("strategyReadiness.blocked_claim_labels");
    expect(routeSource).toContain("row.advertising_channel_type_label");
    expect(routeSource).toContain("row.campaign_status_label");
    expect(routeSource).toContain("row.budget_period_label");
    expect(routeSource).toContain("row.blocked_claim_labels");
    expect(routeSource).toContain("row.payload_preview.operation_type_label");
    expect(routeSource).toContain("row.missing_read_contract_labels");
    expect(routeSource).not.toContain("adsOptimizerReadinessTitle");
    expect(routeSource).not.toContain("adsOptimizerReadinessSummary");
    expect(routeSource).not.toContain("adsOptimizerReadinessNextStep");
    expect(routeSource).not.toContain("adsOptimizerReadinessItemLabel");
    expect(routeSource).not.toContain("adsOptimizerModeLabel");
    expect(routeSource).not.toContain("adsBusinessUseLabel");
    expect(routeSource).not.toContain("adsStrategyReviewStatusLabel");
    expect(routeSource).not.toContain("adsCampaignReviewReason");
    expect(routeSource).not.toContain("adsCampaignTriageReason");
    expect(routeSource).not.toContain("interpretation.interpretation_contract");
    expect(routeSource).not.toContain("interpretation.status}");
    expect(routeSource).not.toContain(
      "summary.missing_read_contracts.map(adsMissingReadContractLabel)"
    );
    expect(routeSource).not.toContain(
      "interpretation.missing_requirements.map(adsMissingReadContractLabel)"
    );
    expect(routeSource).not.toContain(
      "strategyReadiness.missing_read_contracts.map(adsMissingReadContractLabel)"
    );
    expect(routeSource).not.toContain(
      "strategyReadiness.blocked_claims.map(adsBlockedClaimLabel)"
    );
    expect(routeSource).not.toContain("summary.blocked_claims.map(adsBlockedClaimLabel)");
  });

  it("custom segments route renders dedicated validation contract", async () => {
    renderApp("/ads-doctor/custom-segments");
    await waitFor(() =>
      expect(
        screen.getByRole("heading", { name: "Segmenty z haseł" })
      ).toBeInTheDocument()
    );

    expect(
      screen.getByText("Status segmentów i dowodów z wyszukiwanych haseł")
    ).toBeInTheDocument();
    expect(screen.getByText("Co marketer może przygotować teraz")).toBeInTheDocument();
    expect(screen.getByText("Dowody i ograniczenia segmentów")).toBeInTheDocument();
    expect(screen.getAllByText("Zapytania użytkowników: Ekologus Search").length).toBeGreaterThan(0);
    const customSegmentCards = screen
      .getAllByText("Zapytania użytkowników: Ekologus Search")
      .map((title) => title.closest("article"))
      .filter((card): card is HTMLElement => card !== null);
    expect(customSegmentCards.length).toBeGreaterThan(1);
    for (const card of customSegmentCards) {
      expect(within(card).queryByText(/ev_/)).not.toBeInTheDocument();
    }
    expect(screen.getAllByText(/Hasła źródłowe:.*bdo rejestracja/).length).toBeGreaterThan(0);
    expect(screen.getByText(/Brakujące kontrakty/)).toBeInTheDocument();
    expect(screen.getByText(/Wymaga oceny/)).toBeInTheDocument();
    expect(screen.getByText(/nie twierdzi, że segment ma zasięg/)).toBeInTheDocument();
    expect(screen.getByText(/Tryb Codexa: Segmenty z haseł/)).toBeInTheDocument();
    expect(screen.queryByText(/skill=wilq-custom-segments/)).not.toBeInTheDocument();
    expect(screen.queryByText("/api/codex/context-pack")).not.toBeInTheDocument();
    expect(screen.queryByText("Evidence Registry")).not.toBeInTheDocument();
    expect(screen.queryByText("Connector Refresh Runs")).not.toBeInTheDocument();
    expect(screen.queryByText("Social Publishing Focus")).not.toBeInTheDocument();
    const routeSource = readFileSync("src/routes/CustomSegmentsDiagnosticSurface.tsx", "utf8");
    expect(routeSource).toContain("missing_read_contract_labels");
    expect(routeSource).toContain("blocked_claim_labels");
    expect(routeSource).toContain("validation_status_label");
    expect(routeSource).not.toContain("from \"./marketingLabels\"");
    expect(routeSource).not.toContain(".map(adsMissingReadContractLabel)");
    expect(routeSource).not.toContain(".map(adsBlockedClaimLabel)");
  });

  it("legacy operating routes do not fall back to registry dumps", async () => {
    renderApp("/ads-doctor/search-terms");
    await waitFor(() => expect(screen.getByRole("heading", { name: "Widok WILQ" })).toBeInTheDocument());
    expect(screen.queryByText("Expert Rules")).not.toBeInTheDocument();
    expect(screen.queryByText("Evidence Registry")).not.toBeInTheDocument();
    expect(screen.queryByText("Connector Refresh Runs")).not.toBeInTheDocument();
  });

  it("workflow route renders persisted workflow runs", async () => {
    renderApp("/workflows");
    await waitFor(() => expect(screen.getByText("Ostatnie uruchomienia")).toBeInTheDocument());
    expect(screen.getByRole("heading", { name: "Procesy WILQ" })).toBeInTheDocument();
    expect(screen.getByText("Procesy decyzyjne")).toBeInTheDocument();
    expect(screen.getAllByText("Plan dnia WILQ").length).toBeGreaterThan(0);
    expect(screen.getByText("gotowe")).toBeInTheDocument();
    expect(screen.queryByText("status wymaga opisu")).not.toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Pokaż opis procesu" }).length).toBeGreaterThan(0);
    expect(screen.queryByText(/werdykt zwrotu z reklam/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Polecenie Codex: dostępne/)).not.toBeInTheDocument();
    expect(screen.getAllByText(/Braki:/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Zakazane obietnice:/).length).toBeGreaterThan(0);
    expect(screen.queryByText(/wzrost konwersji/)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Pokaż uruchomienia (1)" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Pokaż wyniki procesów" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Pokaż powiązane akcje (1)" })).toBeInTheDocument();
    expect(screen.queryByText("queued")).not.toBeInTheDocument();
    expect(screen.queryByText("Dowody z procesów")).not.toBeInTheDocument();
    expect(screen.queryByText(/GOOGLE_ADS \/ PREPARE/)).not.toBeInTheDocument();
    expect(screen.queryByText("daily_command")).not.toBeInTheDocument();
    expect(screen.queryByText("run_daily_command_test")).not.toBeInTheDocument();
    expect(screen.queryByText("localo_visibility_review")).not.toBeInTheDocument();
    expect(screen.queryByText("localo")).not.toBeInTheDocument();
    expect(screen.queryByText(/wilq-daily-command/)).not.toBeInTheDocument();
    expect(screen.queryByText(/local_ranking_rows/)).not.toBeInTheDocument();
    expect(screen.getByText("Wyniki procesów")).toBeInTheDocument();
    expect(screen.queryByText("Rejestr workflowów")).not.toBeInTheDocument();
    expect(screen.queryByText("Workflowy WILQ")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Pokaż uruchomienia (1)" }));
    expect(await screen.findByText("queued")).toBeInTheDocument();
    expect(screen.queryByText("run_daily_command_test")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Pokaż wyniki procesów" }));
    expect(screen.getByText("Dowody z procesów")).toBeInTheDocument();
    expect(screen.getByText("Akcje z procesów")).toBeInTheDocument();
  });

  it("knowledge route renders compiled cards and playbooks", async () => {
    renderApp("/knowledge");
    await waitFor(() => expect(screen.getByText("Ocena Ads")).toBeInTheDocument());
    expect(screen.getByText("Co ta wiedza zmienia w decyzjach")).toBeInTheDocument();
    expect(screen.getByText("Ocena Ads")).toBeInTheDocument();
    expect(screen.getByText("Co zrobić dalej")).toBeInTheDocument();
    expect(screen.getByText("Dowody: 1")).toBeInTheDocument();
    expect(screen.getByText("Źródła danych: 1 źródło")).toBeInTheDocument();
    expect(screen.getByText("Akcje do sprawdzenia: 1 akcja")).toBeInTheDocument();
    expect(screen.getByText("Zakazane obietnice: 1")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Pokaż pełną mapę wiedzy" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Pokaż źródła wiedzy" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Pokaż zasady pracy" })).toBeInTheDocument();
    expect(screen.queryByText("Skill: dostępny")).not.toBeInTheDocument();
    expect(screen.queryByText("Karty wiedzy: 1")).not.toBeInTheDocument();
    expect(screen.queryByText("Playbooki: 1")).not.toBeInTheDocument();
    expect(screen.queryByText("Reguły eksperckie: 1")).not.toBeInTheDocument();
    expect(screen.queryByText(/card_google_ads_search_playbook/)).not.toBeInTheDocument();
    expect(screen.queryByText(/google_ads_search_playbook/)).not.toBeInTheDocument();
    expect(screen.queryByText(/ads_search_terms_v1/)).not.toBeInTheDocument();
    expect(screen.queryByText(/local_ranking_rows/)).not.toBeInTheDocument();
    expect(screen.queryByText("Powiązania")).not.toBeInTheDocument();
    expect(screen.queryByText("wzorzec Ads / playbook marketingowy")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Pokaż źródła wiedzy" }));
    expect(
      screen.getAllByText("Diagnostyka wyszukiwanych haseł Google Ads").length
    ).toBeGreaterThan(0);
    expect(screen.queryByText("Google Ads search diagnostics")).not.toBeInTheDocument();
    const playbooksToggle = screen.getByRole("button", { name: "Pokaż zasady pracy" });
    fireEvent.click(playbooksToggle);
    expect(playbooksToggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.queryByText("Wymagane dowody: search_terms, evidence_ids")).not.toBeInTheDocument();
    expect(screen.queryByText("Evidence-backed search-term opportunity.")).not.toBeInTheDocument();
    expect(screen.queryByText("Knowledge Cards")).not.toBeInTheDocument();
    expect(screen.queryByText("Machine-Readable Playbooks")).not.toBeInTheDocument();
    expect(screen.queryByText("Evidence Registry")).not.toBeInTheDocument();
    expect(screen.queryByText("Connector Refresh Runs")).not.toBeInTheDocument();
    expect(screen.queryByText("Expert Rules")).not.toBeInTheDocument();
    expect(screen.queryByText("Connector Status")).not.toBeInTheDocument();
  });

  it("knowledge route shows its layout while the operating map is still loading", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/api/knowledge/cards")) {
          return Promise.resolve(Response.json(knowledgeCards));
        }
        if (url.endsWith("/api/knowledge/playbooks")) {
          return Promise.resolve(Response.json(playbooks));
        }
        if (url.endsWith("/api/knowledge/operating-map")) {
          return new Promise<Response>(() => {});
        }
        return Promise.resolve(Response.json({}));
      })
    );

    renderApp("/knowledge");

    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "Baza wiedzy WILQ" })).toBeInTheDocument()
    );
    expect(screen.getByText("Co ta wiedza zmienia w decyzjach")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Pokaż pełną mapę wiedzy" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Pokaż źródła wiedzy" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Pokaż zasady pracy" })).toBeInTheDocument();
    expect(screen.getAllByText("Ładowanie stanu WILQ").length).toBe(1);
  });

  it("merchant route renders dedicated feed diagnostics", async () => {
    renderApp("/merchant");
    await waitFor(() =>
      expect(
        screen.getByRole("heading", { name: "Merchant Center" })
      ).toBeInTheDocument()
    );
    expect(screen.getByRole("heading", { name: "Pełny przegląd Merchant" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Pokaż pełny przegląd Merchant" })).toBeInTheDocument();
    expect(screen.queryByText("Dowody i ograniczenia Merchant")).not.toBeInTheDocument();
    expect(screen.queryByText("Czego nie wiemy z Merchant API")).not.toBeInTheDocument();
    expect(screen.queryByText("Gotowość próbek produktów")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Pokaż pełny przegląd Merchant" }));
    expect(await screen.findByText("Dowody i ograniczenia Merchant")).toBeInTheDocument();
    expect(screen.queryByText("Merchant Center: feed/product health")).not.toBeInTheDocument();
    expect(screen.queryByText("Merchant Center: kolejka feed/product issues")).not.toBeInTheDocument();
    expect(screen.getByText("Co marketer ma zrobić teraz z feedem")).toBeInTheDocument();
    expect(screen.getByText("Bezpieczny tryb pracy")).toBeInTheDocument();
    expect(screen.getByText(/WILQ grupuje problemy Merchant po typie/)).toBeInTheDocument();
    expect(
      screen.getByText("Merchant: sprawdź zmiana dostępności do sprawdzenia / dostępność")
    ).toBeInTheDocument();
    const merchantDecisionCard = screen
      .getByText("Merchant: sprawdź zmiana dostępności do sprawdzenia / dostępność")
      .closest("article");
    expect(merchantDecisionCard).not.toBeNull();
    expect(within(merchantDecisionCard as HTMLElement).queryByText(/ev_/)).not.toBeInTheDocument();
    expect(within(merchantDecisionCard as HTMLElement).queryByText(/act_/)).not.toBeInTheDocument();
    expect(screen.getByText(/przegląd problemu feedu/)).toBeInTheDocument();
    expect(
      screen.getByText(
        /23 zgłoszeń problemu bez wpływu \/ wymaga działania po stronie Merchant dla PL \/ reklamy produktowe/
      )
    ).toBeInTheDocument();
    expect(screen.getAllByText("Zgłoszenia").length).toBeGreaterThan(0);
    expect(screen.queryByText("zgłoszenia: 23")).not.toBeInTheDocument();
    expect(screen.getByText("problem: zmiana dostępności do sprawdzenia")).toBeInTheDocument();
    expect(screen.getByText("atrybut: dostępność")).toBeInTheDocument();
    expect(screen.getByText("kontekst: reklamy produktowe")).toBeInTheDocument();
    expect(screen.queryByText("problem: availability_updated")).not.toBeInTheDocument();
    expect(screen.queryByText("atrybut: n:availability")).not.toBeInTheDocument();
    expect(screen.queryByText("kontekst: SHOPPING_ADS")).not.toBeInTheDocument();
    expect(screen.queryByText("Affected")).not.toBeInTheDocument();
    expect(screen.queryByText("configured")).not.toBeInTheDocument();
    expect(screen.queryByText("Evidence")).not.toBeInTheDocument();
    expect(screen.getByText("dostęp skonfigurowany")).toBeInTheDocument();
    expect(screen.getByText("dane świeże")).toBeInTheDocument();
    expect(screen.getByText("Czego nie wiemy z Merchant API")).toBeInTheDocument();
    expect(
      screen.getByText("Licznik problemów nie jest liczbą unikalnych produktów")
    ).toBeInTheDocument();
    expect(screen.getByText("Gotowość próbek produktów")).toBeInTheDocument();
    expect(screen.getByText("próbki produktów dostępne")).toBeInTheDocument();
    expect(screen.getByText(/Przykładowe produkty:/)).toBeInTheDocument();
    expect(screen.getAllByText(/online~pl~PL~SKU-001/).length).toBeGreaterThan(0);
    expect(screen.getByText(/Przykładowe tytuły:/)).toBeInTheDocument();
    expect(screen.getAllByText(/Sorbent chemiczny 10 kg/).length).toBeGreaterThan(0);
    expect(
      screen.getByText(/Obecny odczyt: merchant_aggregate_product_statuses/)
    ).toBeInTheDocument();
    expect(screen.getByText("Produkty połączone z Ads/GA4")).toBeInTheDocument();
    expect(screen.getByText("dane Ads/GA4 zablokowane")).toBeInTheDocument();
    expect(screen.getByText(/google_ads_shopping_product_performance/)).toBeInTheDocument();
    expect(screen.getByText("Wpływ ceny produktu")).toBeInTheDocument();
    expect(screen.getByText("wpływ ceny zablokowany")).toBeInTheDocument();
    expect(screen.getByText("Zmiany ceny")).toBeInTheDocument();
    expect(screen.getByText("Bez zmiany")).toBeInTheDocument();
    expect(screen.getAllByText(/google_ads_shopping_product_price_history/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/zwrot z reklam na poziomie produktu/).length).toBeGreaterThan(0);
    expect(screen.getByText("Brak połączenia produktów Merchant z Ads/GA4")).toBeInTheDocument();
    expect(screen.getByText("metryki feedu dostępne")).toBeInTheDocument();
    expect(screen.getAllByText("Dowody").length).toBeGreaterThan(0);
    expect(screen.getByText(/Przykładowe produkty służą tylko do ręcznego/)).toBeInTheDocument();
    expect(screen.getByText("Przykładowe produkty do sprawdzenia")).toBeInTheDocument();
    expect(screen.queryByText(/surowy opis techniczny|techniczny model akcji/i)).not.toBeInTheDocument();
    expect(screen.getAllByText(/ponowne zatwierdzenie produktu/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/automatyczna zmiana feedu/).length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: "Sprawdź w WILQ" })).toHaveAttribute(
      "href",
      "/actions/act_review_merchant_feed_issues"
    );
    expect(screen.queryByText("Merchant: NOT_IMPACTED / availability_updated / PL")).not.toBeInTheDocument();
    expect(screen.queryByText(/total_products: 10900/)).not.toBeInTheDocument();
    expect(screen.getByText("Produkty w feedzie")).toBeInTheDocument();
    expect(screen.getAllByText(/ev_refresh_merchant_feed/).length).toBeGreaterThan(0);
    const merchantProofSection = screen
      .getByText("Dowody i ograniczenia Merchant")
      .closest("section");
    expect(merchantProofSection).not.toBeNull();
    const merchantProof = within(merchantProofSection as HTMLElement);
    expect(merchantProof.getByText(/Przykładowe dowody/)).toBeInTheDocument();
    expect(screen.getByText("Łącznie dowodów")).toBeInTheDocument();
    expect(merchantProof.queryByText(/ev_refresh_merchant_safety/)).not.toBeInTheDocument();
    expect(screen.getByText("Akcje do sprawdzenia")).toBeInTheDocument();
    expect(
      screen.queryByText("Przygotuj kolejkę przeglądu feedu Merchant Center")
    ).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Pokaż akcje do sprawdzenia" }));
    expect(
      screen.getByText("Przygotuj kolejkę przeglądu feedu Merchant Center")
    ).toBeInTheDocument();
    expect(screen.getByText(/Zapis zmian:/)).toBeInTheDocument();
    expect(screen.getByText("Warunki przeglądu")).toBeInTheDocument();
    expect(screen.getByText("czeka na sprawdzenie")).toBeInTheDocument();
    expect(screen.getByText(/podgląd zmian nie pozwala na zapis/)).toBeInTheDocument();
    expect(screen.getByText("Ostatni zapis bezpieczeństwa")).toBeInTheDocument();
    expect(screen.getByText("Zapisano kontrolę bezpieczeństwa bez zmian w zewnętrznych systemach.")).toBeInTheDocument();
    expect(screen.getByText(/brak bezpiecznej ścieżki zapisu w zewnętrznym systemie/)).toBeInTheDocument();
    expect(screen.queryByText("Ostatni audyt zmiany")).not.toBeInTheDocument();
    expect(screen.queryByText(/Adapter:/)).not.toBeInTheDocument();
    expect(screen.getByText("Wynik przeglądu człowieka")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Zapisz przegląd" }));
    await waitFor(() =>
      expect(screen.getByText("Zapisano sprawdzenie: Przegląd operatora zapisany")).toBeInTheDocument()
    );
    expect(screen.getByText("Podgląd zmian")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Generuj podgląd" }));
    await waitFor(() => expect(screen.getByText("Ślad bezpieczeństwa: Podgląd zmian wygenerowany")).toBeInTheDocument());
    expect(screen.getByText(/Bez zapisu zmian: tak; zapis zmian:\s*zablokowane/)).toBeInTheDocument();
    expect(screen.getByText("Jawne potwierdzenie podglądu")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Potwierdź podgląd" }));
    await waitFor(() => expect(screen.getByText("Ślad bezpieczeństwa: Podgląd potwierdzony")).toBeInTheDocument());
    expect(screen.getByText("Potwierdzenie:")).toBeInTheDocument();
    expect(screen.getByText("potwierdzony")).toBeInTheDocument();
    expect(screen.getByText(/Zapis zmian nadal: zablokowany/)).toBeInTheDocument();
    expect(screen.getByText("Sprawdzenie efektu")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Sprawdź efekt" }));
    await waitFor(() =>
      expect(screen.getByText("Ślad bezpieczeństwa: Sprawdzenie efektu zapisane")).toBeInTheDocument()
    );
    expect(screen.getByText("Sprawdzenie efektu:")).toBeInTheDocument();
    expect(screen.getByText("zapisane")).toBeInTheDocument();
    expect(screen.getByText("Metryki z dowodami: 2")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Sprawdź w WILQ" }));
    await waitFor(() => expect(screen.getByText("Wynik:")).toBeInTheDocument());
    expect(screen.getByText("poprawna")).toBeInTheDocument();
    expect(screen.getByText("Błędy: brak")).toBeInTheDocument();
    expect(
      screen.getAllByRole("link", { name: "Sprawdź w WILQ" })[0]
    ).toHaveAttribute("href", "/actions/act_review_merchant_feed_issues");
    expect(
      screen.getAllByRole("link", { name: "ev_refresh_merchant_feed" })[0]
    ).toHaveAttribute("href", "/evidence/ev_refresh_merchant_feed");
  });

  it("ga4 route renders workflow-specific brief focus", async () => {
    renderApp("/ga4");
    await waitFor(
      () => expect(screen.getByRole("heading", { name: /^GA4$/ })).toBeInTheDocument(),
      { timeout: 5_000 }
    );
    expect(screen.getByText("Status GA4 / pomiar i jakość ruchu")).toBeInTheDocument();
    expect(screen.getByText("dane świeże")).toBeInTheDocument();
    expect(screen.queryByText("status wymaga opisu")).not.toBeInTheDocument();
    expect(screen.queryByText("google_ads")).not.toBeInTheDocument();
    expect(screen.queryByText("google_analytics_4")).not.toBeInTheDocument();
    expect(screen.queryByText("wordpress_ekologus")).not.toBeInTheDocument();
    expect(screen.getAllByText(/Ostatni odczyt danych GA4 mieści się/).length).toBeGreaterThan(0);
    expect(screen.getByText("Pełny przegląd GA4")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Pokaż pełny przegląd GA4" })).toBeInTheDocument();
    expect(screen.getByText("Akcje do sprawdzenia")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Pokaż akcje do sprawdzenia" })).toBeInTheDocument();
    expect(screen.queryByText("Problemy pomiaru GA4")).not.toBeInTheDocument();
    expect(screen.queryByText("Dowody i ograniczenia GA4")).not.toBeInTheDocument();
    expect(screen.queryByText("Podgląd przeglądu GA4")).not.toBeInTheDocument();
    expect(screen.queryByText("Brama bezpieczeństwa GA4")).not.toBeInTheDocument();
    expect(
      screen.queryByText("Sprawdź jakość pomiaru GA4 przed oceną kampanii")
    ).not.toBeInTheDocument();
    expect(screen.getByText("Co marketer ma sprawdzić teraz w jakości ruchu")).toBeInTheDocument();
    expect(screen.getByText("Bezpieczny tryb analityki")).toBeInTheDocument();
    expect(screen.getByText(/Brak metryk konwersji oznacza/)).toBeInTheDocument();
    expect(screen.getByText(/Konwersje i zdarzenia kluczowe/)).toBeInTheDocument();
    expect(screen.getByText(/blokuje wnioski o konwersjach/)).toBeInTheDocument();
    expect(screen.getByText(/powiązanie konwersji i zdarzeń kluczowych/)).toBeInTheDocument();
    expect(screen.getByText("Sprawdź stronę wejścia: /oferta/")).toBeInTheDocument();
    expect(screen.queryByText(/mapowanie konwersji/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Sprawdź mapowanie strony wejścia/)).not.toBeInTheDocument();
    expect(screen.getByText("aktywni")).toBeInTheDocument();
    expect(screen.getByText("sesje")).toBeInTheDocument();
    expect(screen.getByText("zaangażowanie")).toBeInTheDocument();
    expect(screen.getAllByText(/Strona wejścia: \/oferta\//).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Źródło: google \/ cpc/).length).toBeGreaterThan(0);
    expect(screen.getByText(/WordPress: brak potwierdzenia/)).toBeInTheDocument();
    expect(screen.getAllByText(/Gotowość pomiaru/).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "Pokaż pełny przegląd GA4" }));
    expect(screen.getByText("Problemy pomiaru GA4")).toBeInTheDocument();
    expect(screen.getByText("Dowody i ograniczenia GA4")).toBeInTheDocument();
    expect(screen.queryByText("google_ads")).not.toBeInTheDocument();
    expect(screen.queryByText("google_analytics_4")).not.toBeInTheDocument();
    expect(screen.queryByText("wordpress_ekologus")).not.toBeInTheDocument();
    expect(screen.queryByText(/Tracking readiness/)).not.toBeInTheDocument();
    expect(screen.queryByText("GA4: landing page, źródło i kampania behavior")).not.toBeInTheDocument();
    expect(screen.queryByText("GA4: tracking/conversion readiness")).not.toBeInTheDocument();
    expect(screen.getByText("Podgląd przeglądu GA4")).toBeInTheDocument();
    expect(screen.queryByText(/Surowa kolejka akcji/i)).not.toBeInTheDocument();
    expect(screen.queryByText("Analytics Safety Gate")).not.toBeInTheDocument();
    expect(screen.getByText("Brama bezpieczeństwa GA4")).toBeInTheDocument();
    expect(screen.getAllByText("Aktywni użytkownicy").length).toBeGreaterThan(0);
    expect(screen.queryByText(/active_users: 20/)).not.toBeInTheDocument();
    const ga4MeasurementSection = screen
      .getByText("Problemy pomiaru GA4")
      .closest("section");
    expect(ga4MeasurementSection).not.toBeNull();
    const ga4MeasurementCopy = ga4MeasurementSection?.textContent ?? "";
    expect(ga4MeasurementCopy).not.toMatch(/ev_/);
    expect(ga4MeasurementCopy).not.toMatch(/act_/);
    const ga4OperatorSection = screen
      .getByText("Operator GA4")
      .closest("section");
    expect(ga4OperatorSection).not.toBeNull();
    const ga4OperatorCopy = ga4OperatorSection?.textContent ?? "";
    expect(ga4OperatorCopy).not.toMatch(/ev_/);
    expect(ga4OperatorCopy).not.toMatch(/act_/);
    expect(
      within(ga4OperatorSection as HTMLElement).getByRole("link", { name: "Sprawdź GA4 w WILQ" })
    ).toHaveAttribute("href", "/actions/act_review_ga4_tracking_quality");
    const ga4ProofSection = screen
      .getByText("Dowody i ograniczenia GA4")
      .closest("section");
    expect(ga4ProofSection).not.toBeNull();
    const ga4Proof = within(ga4ProofSection as HTMLElement);
    expect(ga4Proof.queryByText(/active_users: 20/)).not.toBeInTheDocument();
    expect(ga4Proof.getByText(/Przykładowe dowody/)).toBeInTheDocument();
    expect(ga4Proof.getByText("Łącznie dowodów")).toBeInTheDocument();
    expect(ga4Proof.queryByText(/ev_refresh_ga4_safety/)).not.toBeInTheDocument();
    expect(
      ga4Proof.queryByRole("link", { name: "act_review_ga4_tracking_quality" })
    ).not.toBeInTheDocument();
    expect(ga4Proof.getByText(/1 akcja/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Pokaż akcje do sprawdzenia" }));
    expect(
      screen.getByText("Sprawdź jakość pomiaru GA4 przed oceną kampanii")
    ).toBeInTheDocument();
    expect(screen.getByText(/Zapis zmian zablokowany/i)).toBeInTheDocument();
  });

  it("content route renders condensed selected decision with expandable detail", async () => {
    renderApp("/content-planner");
    await waitFor(
      () => expect(screen.getByText("Status SEO / Content")).toBeInTheDocument(),
      { timeout: 5_000 }
    );
    expect(screen.getByText("Czy można pisać?")).toBeInTheDocument();
    expect(screen.getByText("Rekomendowany kierunek")).toBeInTheDocument();
    expect(screen.getAllByText("odświeżyć").length).toBeGreaterThan(0);
    expect(screen.getAllByText("wymaga sprawdzenia").length).toBeGreaterThan(0);
    expect(screen.getByText(/Szkic i WordPress pozostają zablokowane/)).toBeInTheDocument();
    expect(screen.getByText("Plany treści do sprawdzenia")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Pokaż plany treści" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Pokaż pełny przegląd Content" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Pokaż akcje do sprawdzenia" })).toBeInTheDocument();
    expect(screen.queryByText("google_ads")).not.toBeInTheDocument();
    expect(screen.queryByText("google_analytics_4")).not.toBeInTheDocument();
    expect(screen.queryByText("wordpress_ekologus")).not.toBeInTheDocument();
    expect(screen.queryByText("Co marketer ma zrobić teraz z treściami")).not.toBeInTheDocument();
    expect(screen.queryByText("Bezpieczny tryb treści")).not.toBeInTheDocument();
    expect(screen.queryByText("Dowody i ograniczenia Content")).not.toBeInTheDocument();
    expect(screen.queryByText("Brama bezpieczeństwa treści")).not.toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getAllByText(/Ahrefs: zweryfikuj luki SEO/).length).toBeGreaterThan(0)
    );
    const contentDecisionCard = screen
      .getAllByText(/Ahrefs: zweryfikuj luki SEO/)[0]
      .closest("section");
    expect(contentDecisionCard).not.toBeNull();
    expect(within(contentDecisionCard as HTMLElement).queryByText(/ev_/)).not.toBeInTheDocument();
    expect(
      within(contentDecisionCard as HTMLElement).queryByText(/act_(prepare|review|configure|apply)/)
    ).not.toBeInTheDocument();
    expect(within(contentDecisionCard as HTMLElement).getByText("rekordy Ahrefs")).toBeInTheDocument();
    expect(within(contentDecisionCard as HTMLElement).getByText("pasujące")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Sprawdź w WILQ" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Pokaż pełny przegląd Content" }));
    expect(screen.getByText("Co marketer ma zrobić teraz z treściami")).toBeInTheDocument();
    expect(screen.getByText("Bezpieczny tryb treści")).toBeInTheDocument();
    expect(screen.queryByText("google_ads")).not.toBeInTheDocument();
    expect(screen.queryByText("google_analytics_4")).not.toBeInTheDocument();
    expect(screen.queryByText("wordpress_ekologus")).not.toBeInTheDocument();
    expect(
      screen.getByText(/WILQ łączy zapytania i URL-e z GSC ze spisem treści WordPress/)
    ).toBeInTheDocument();
    const contentSafeMode = screen
      .getByText("Bezpieczny tryb treści")
      .closest(".rounded-md");
    expect(contentSafeMode).not.toBeNull();
    expect(within(contentSafeMode as HTMLElement).queryByText(/ev_/)).not.toBeInTheDocument();
    expect(
      within(contentSafeMode as HTMLElement).queryByText(/act_(prepare|review|configure|apply)/)
    ).not.toBeInTheDocument();
    expect(screen.getByText("Dowody i ograniczenia Content")).toBeInTheDocument();
    expect(screen.queryByText("GSC: query/page matrix")).not.toBeInTheDocument();
    expect(screen.queryByText("WordPress: inventory protection")).not.toBeInTheDocument();
    expect(screen.queryByText("WordPress match: found")).not.toBeInTheDocument();
    expect(screen.getByText("Brama bezpieczeństwa treści")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "act_prepare_content_refresh_queue" })).not.toBeInTheDocument();
    expect(screen.queryByText(/clicks: 12/)).not.toBeInTheDocument();
    expect(screen.getAllByText("Kliknięcia").length).toBeGreaterThan(0);
    const contentProofSection = screen
      .getByText("Dowody i ograniczenia Content")
      .closest("section");
    expect(contentProofSection).not.toBeNull();
    const contentProof = within(contentProofSection as HTMLElement);
    expect(contentProof.getByText(/Przykładowe dowody/)).toBeInTheDocument();
    expect(contentProof.getByText("Łącznie dowodów")).toBeInTheDocument();
    expect(contentProof.queryByText(/ev_refresh_content_safety/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Pokaż plany treści" }));
    expect(screen.getByText("Co WILQ może przygotować bez publikacji")).toBeInTheDocument();
    expect(screen.getByText("wersja robocza istniejącej treści / szkic")).toBeInTheDocument();
    expect(screen.queryByText("wersja robocza istniejącej treści / draft")).not.toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: "Zapisz sprawdzenie planu treści" })[0]);
    await waitFor(() =>
      expect(
        screen.getByText(/Zapisano sprawdzenie: Przegląd operatora zapisany/)
      ).toBeInTheDocument()
    );
    fireEvent.click(screen.getByRole("button", { name: "Pokaż akcje do sprawdzenia" }));
    expect(
      screen.getByText("Przygotuj kolejkę odświeżenia treści ekologus.pl")
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Sprawdź w WILQ" }));
    await waitFor(() => expect(screen.getByText("Wynik:")).toBeInTheDocument());
    expect(screen.getByText("poprawna")).toBeInTheDocument();
  });

  it("localo route renders workflow-specific blockers and clean metric labels", async () => {
    renderApp("/localo");
    await waitFor(
      () => expect(screen.getByRole("heading", { name: "Localo" })).toBeInTheDocument(),
      { timeout: 10_000 }
    );
    expect(screen.getByText("Status Localo / widoczność lokalna")).toBeInTheDocument();
    expect(screen.getByText("Aktualny odczyt lokalnej widoczności")).toBeInTheDocument();
    expect(screen.getByText("Co marketer ma wiedzieć o Localo")).toBeInTheDocument();
    expect(screen.getByText("Dowody i ograniczenia Localo")).toBeInTheDocument();
    expect(
      screen.getByText("Dostęp Localo działa; brakuje rankingów i danych profilu firmy w Google")
    ).toBeInTheDocument();
    expect(screen.queryByText("dostęp MCP")).not.toBeInTheDocument();
    expect(screen.getAllByText("dane Localo").length).toBeGreaterThan(0);
    expect(screen.getAllByText("brakujące dane").length).toBeGreaterThan(0);
    expect(screen.getByText("blokady obietnic")).toBeInTheDocument();
    expect(screen.queryByText(/metryka WILQ/)).not.toBeInTheDocument();
    expect(screen.queryByText(/local_rankings/)).not.toBeInTheDocument();
    expect(screen.queryByText(/active_places/)).not.toBeInTheDocument();
    expect(
      screen.getByText("Nie wyciągaj wniosków o lokalnej widoczności bez danych Localo")
    ).toBeInTheDocument();
    expect(screen.getAllByText("dostęp działa").length).toBeGreaterThan(0);
    expect(screen.getByText("Brama bezpieczeństwa Localo i profilu firmy w Google")).toBeInTheDocument();
    const localoDecisionCard = screen
      .getByText("Dostęp Localo działa; brakuje rankingów i danych profilu firmy w Google")
      .closest("article");
    expect(localoDecisionCard).not.toBeNull();
    expect(within(localoDecisionCard as HTMLElement).queryByText(/ev_/)).not.toBeInTheDocument();
    const localoSafetyGate = screen
      .getByText("Brama bezpieczeństwa Localo i profilu firmy w Google")
      .closest("section");
    expect(localoSafetyGate).not.toBeNull();
    expect(within(localoSafetyGate as HTMLElement).queryByText(/ev_/)).not.toBeInTheDocument();
    expect(screen.queryByText("Test dostępu")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Pokaż szczegóły techniczne Localo" }));
    expect(screen.getByText("Test dostępu")).toBeInTheDocument();
    expect(screen.queryByText("Local Visibility Focus")).not.toBeInTheDocument();
    expect(screen.queryByText("Taktyki z WILQ")).not.toBeInTheDocument();
    expect(screen.queryByText("Metric facts")).not.toBeInTheDocument();
    expect(screen.queryByText("24 Taktyki")).not.toBeInTheDocument();
    expect(screen.queryByText("Dokończ Localo access")).not.toBeInTheDocument();
    expect(
      vi.mocked(fetch).mock.calls.some(([url]) =>
        String(url).endsWith("/api/marketing/tactical-queue")
      )
    ).toBe(false);
  });

  it("social route renders workflow-specific blockers", async () => {
    renderApp("/social-publisher");
    await waitFor(
      () =>
        expect(screen.getByRole("heading", { name: "Publikacje social" })).toBeInTheDocument(),
      { timeout: 10_000 }
    );
    expect(screen.getByText("Publikacje social do sprawdzenia")).toBeInTheDocument();
    expect(screen.queryByText("Social Publishing Focus")).not.toBeInTheDocument();
    expect(screen.getByText("LinkedIn: brakuje organizacji i access tokena")).toBeInTheDocument();
  });

  it("content route keeps review language clean in expanded workflows", async () => {
    renderApp("/content-planner");
    await waitFor(
      () => expect(screen.getByText("Status SEO / Content")).toBeInTheDocument(),
      { timeout: 10_000 }
    );
    expect(screen.getAllByText("GSC↔WP").length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText("Ahrefs↔WP").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("Adresy i podgląd")).toBeInTheDocument();
    expect(screen.queryByText(/URL do sprawdzenia:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Review URL-i:/)).not.toBeInTheDocument();
    expect(screen.queryByText("Input do kontroli URL-i")).not.toBeInTheDocument();
    expect(screen.queryByText(/Kandydat: content_brief_gsc_/)).not.toBeInTheDocument();
    expect(
      screen.queryByText("Review: zapisz kontrolę URL-i przez akcję do sprawdzenia")
    ).not.toBeInTheDocument();
    expect(screen.queryByText("Payload: 4 checked items")).not.toBeInTheDocument();
    expect(screen.queryByText("Dopasowania WP")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Pokaż pełny przegląd Content" }));
    expect(screen.getAllByText("Dowody i ograniczenia Content").length).toBeGreaterThan(0);
    expect(screen.queryByText("WordPress: inventory protection")).not.toBeInTheDocument();
    expect(
      screen.getAllByText("Ahrefs: zweryfikuj luki SEO przed planem treści").length
    ).toBeGreaterThan(0);
    expect(screen.getByText("sprawdzenie luk Ahrefs")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Pokaż plany treści" }));
    await waitFor(() =>
      expect(screen.getByText("Plany treści do sprawdzenia")).toBeInTheDocument()
    );
    expect(screen.getByText("Co WILQ może przygotować bez publikacji")).toBeInTheDocument();
    expect(screen.getByText("Google Search Console / odświeżenie")).toBeInTheDocument();
    expect(screen.getByText("Ahrefs do sprawdzenia / sprawdzenie")).toBeInTheDocument();
    expect(screen.getByText(/Kąt treści: Odśwież istniejącą treść/)).toBeInTheDocument();
    expect(screen.getByText(/Odbiorca: Decydent środowiskowy/)).toBeInTheDocument();
    expect(screen.getByText(/CTA: CTA do rozmowy/)).toBeInTheDocument();
    expect(screen.getByText(/czy tekst jest aktualny prawnie/)).toBeInTheDocument();
    expect(screen.getByText(/brak dowodu wzrost liczby leadów/)).toBeInTheDocument();
    expect(screen.getAllByText("audyt środowiskowy").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("GSC: jest")).toBeInTheDocument();
    expect(screen.getByText("WP: jest")).toBeInTheDocument();
    expect(screen.getByText("Overlap GSC: audyt środowiskowy")).toBeInTheDocument();
    expect(screen.getByText("Overlap WP: /audyt-srodowiskowy/")).toBeInTheDocument();
    expect(screen.getByText("Szkic WordPress po sprawdzeniu")).toBeInTheDocument();
    expect(screen.getByText("Co WILQ może przygotować jako szkic WordPress")).toBeInTheDocument();
    expect(screen.getByText("Odświeżenie: zielony ład")).toBeInTheDocument();
    expect(screen.getByText("wersja robocza istniejącej treści / szkic")).toBeInTheDocument();
    expect(screen.queryByText("wersja robocza istniejącej treści / draft")).not.toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: "Zapisz sprawdzenie planu treści" })[0]);
    await waitFor(() =>
      expect(
        screen.getByText(/Zapisano sprawdzenie: Przegląd operatora zapisany/)
      ).toBeInTheDocument()
    );
    fireEvent.click(screen.getByRole("button", { name: "Pokaż akcje do sprawdzenia" }));
    expect(
      screen.getByText("Przygotuj kolejkę odświeżenia treści ekologus.pl")
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Sprawdź w WILQ" }));
    await waitFor(() => expect(screen.getByText("Wynik:")).toBeInTheDocument());
    expect(screen.getByText("poprawna")).toBeInTheDocument();
  });

  it("ahrefs route renders authority context and clean gap review language", async () => {
    renderApp("/ahrefs");
    expect(
      await screen.findByRole("heading", { name: "Ahrefs" }, { timeout: 5000 })
    ).toBeInTheDocument();

    expect(screen.getByText("Status Ahrefs / dowody SEO")).toBeInTheDocument();
    expect(screen.getByText("Co marketer ma wiedzieć o Ahrefs")).toBeInTheDocument();
    expect(screen.getByText("Luki SEO z Ahrefs")).toBeInTheDocument();
    expect(screen.getByText("Dowody i ograniczenia Ahrefs")).toBeInTheDocument();
    expect(
      screen.getByText("Użyj Ahrefs tylko jako kontekstu autorytetu")
    ).toBeInTheDocument();
    const ahrefsAuthorityCard = screen
      .getByText("Użyj Ahrefs tylko jako kontekstu autorytetu")
      .closest("article");
    expect(ahrefsAuthorityCard).not.toBeNull();
    expect(within(ahrefsAuthorityCard as HTMLElement).queryByText(/ev_/)).not.toBeInTheDocument();
    expect(screen.getByText("Przejrzyj rekordy luk Ahrefs")).toBeInTheDocument();
    const ahrefsGapCard = screen.getByText("Przejrzyj rekordy luk Ahrefs").closest("article");
    expect(ahrefsGapCard).not.toBeNull();
    expect(within(ahrefsGapCard as HTMLElement).queryByText(/ev_/)).not.toBeInTheDocument();
    const ahrefsGapContract = screen.getByText("Luki SEO z Ahrefs").closest("section");
    expect(ahrefsGapContract).not.toBeNull();
    expect(within(ahrefsGapContract as HTMLElement).queryByText(/ev_/)).not.toBeInTheDocument();
    expect(screen.getAllByText("ocena domeny Ahrefs").length).toBeGreaterThan(0);
    expect(screen.getAllByText("pozycja w rankingu Ahrefs").length).toBeGreaterThan(0);
    expect(screen.getByText("Luki do sprawdzenia")).toBeInTheDocument();
    expect(screen.queryByText(/typed Ahrefs gap records/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/gap read contract/i)).not.toBeInTheDocument();
    expect(screen.queryByText("Gap records")).not.toBeInTheDocument();
    expect(screen.queryByText(/domain_rating: 90/)).not.toBeInTheDocument();
    expect(screen.queryByText("DR")).not.toBeInTheDocument();
    expect(screen.queryByText("Ahrefs Rank")).not.toBeInTheDocument();
    expect(screen.queryByText(/domain_rating=/)).not.toBeInTheDocument();
    expect(screen.queryByText(/ahrefs_rank=/)).not.toBeInTheDocument();
    expect(screen.queryByText("content_gap")).not.toBeInTheDocument();
    expect(screen.queryByText("subdomains")).not.toBeInTheDocument();
    expect(screen.queryByText("completed")).not.toBeInTheDocument();
    const ahrefsProofSection = screen
      .getByText("Dowody i ograniczenia Ahrefs")
      .closest("section");
    expect(ahrefsProofSection).not.toBeNull();
    const ahrefsProof = within(ahrefsProofSection as HTMLElement);
    expect(ahrefsProof.getByText(/Przykładowe dowody/)).toBeInTheDocument();
    expect(ahrefsProof.getByText("Łącznie dowodów")).toBeInTheDocument();
    expect(ahrefsProof.queryByText(/ev_refresh_ahrefs_safety/)).not.toBeInTheDocument();
    expect(screen.getByText("Luka treści: audyt środowiskowy")).toBeInTheDocument();
    expect(screen.getByText("Luka backlinków: example.org")).toBeInTheDocument();
    expect(screen.getByText(/wymagane konkretne rekordy luk Ahrefs/)).toBeInTheDocument();
    expect(screen.getAllByText(/wzrost autorytetu/).length).toBeGreaterThan(0);
    expect(screen.getByText("Pokazuję top 6 z 6 rekordów.")).toBeInTheDocument();
    expect(screen.getByText("Strona konkurencji: hidden-noise.example")).toBeInTheDocument();
    expect(
      screen.queryByText("API-backed operating surface with evidence, connector and action state.")
    ).not.toBeInTheDocument();
    expect(screen.queryByText("Evidence Registry")).not.toBeInTheDocument();
    expect(screen.queryByText("Connector Refresh Runs")).not.toBeInTheDocument();
  });

  it("demand gen route renders readiness contract instead of generic registry", async () => {
    renderApp("/ads-doctor/demand-gen");
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "Demand Gen" })).toBeInTheDocument()
    );

    expect(screen.getByText("Demand Gen: brak kampanii do rekomendacji")).toBeInTheDocument();
    expect(screen.getByText("Co marketer ma wiedzieć przed planem Demand Gen")).toBeInTheDocument();
    expect(screen.getByText("Dowody i ograniczenia Demand Gen")).toBeInTheDocument();
    expect(screen.getByText("kampanie Ads")).toBeInTheDocument();
    expect(screen.getByText("PMax")).toBeInTheDocument();
    expect(screen.getByText("Search")).toBeInTheDocument();
    expect(
      screen.getByText(/W bieżących dowodach Ads nie ma kampanii Demand Gen ani Discovery/)
    ).toBeInTheDocument();
    expect(screen.getAllByText(/wiersze reklam Demand Gen/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/wiersze materiałów kreatywnych/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/akcja do sprawdzenia/i).length).toBeGreaterThan(0);
    expect(screen.getByText("Podgląd sprawdzenia gotowości Demand Gen")).toBeInTheDocument();
    const demandGenOperatorSection = screen
      .getByText("Co marketer ma wiedzieć przed planem Demand Gen")
      .closest("section");
    expect(demandGenOperatorSection).not.toBeNull();
    expect(within(demandGenOperatorSection as HTMLElement).queryByText(/ev_/)).not.toBeInTheDocument();
    expect(
      within(demandGenOperatorSection as HTMLElement).queryByText(/act_(prepare|review|configure|apply)/)
    ).not.toBeInTheDocument();
    expect(screen.getByText(/sprawdzenie kanałów kampanii Ads/)).toBeInTheDocument();
    expect(screen.getAllByText(/jakość stron wejścia według kampanii/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/ograniczenia przejścia/).length).toBeGreaterThan(0);
    expect(screen.getByText(/rekomendacja uruchomienia Demand Gen/)).toBeInTheDocument();
    expect(screen.queryByText(/act_review_demand_gen_readiness/)).not.toBeInTheDocument();
    expect(screen.queryByText(/available_read_contracts/)).not.toBeInTheDocument();
    expect(screen.queryByText(/missing_read_contracts/)).not.toBeInTheDocument();
    expect(screen.queryByText(/read contracts/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/landing quality/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/transition constraints/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/launchu/i)).not.toBeInTheDocument();
    expect(screen.queryByText("DG rows")).not.toBeInTheDocument();
    expect(screen.queryByText("API-backed operating surface")).not.toBeInTheDocument();
    expect(screen.queryByText("Evidence Registry")).not.toBeInTheDocument();
    expect(screen.queryByText("Connector Refresh Runs")).not.toBeInTheDocument();
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
    expect(screen.getByText("Źródło: google_merchant_center")).toBeInTheDocument();
  });
});
