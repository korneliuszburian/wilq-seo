import { cleanup, render, screen, waitFor } from "@testing-library/react";
import type { QueryClient } from "@tanstack/react-query";
import { readFileSync } from "node:fs";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ActionObject } from "../lib/api";
import { App, createWilqQueryClient, createWilqRouter } from "./App";

const actionFixture: ActionObject = {
  id: "act_1",
  title: "Przygotuj kolejkę przeglądu feedu Merchant Center",
  domain: "merchant",
  connector: "google_merchant_center",
  connector_label: "Merchant Center",
  mode: "prepare",
  mode_label: "przygotowanie",
  risk: "medium",
  risk_label: "średnie ryzyko",
  status: "needs_validation",
  status_label: "wymaga sprawdzenia w WILQ",
  evidence_ids: ["ev_refresh_merchant_feed"],
  evidence_summary_label: "1 dowód źródłowy",
  metrics: [],
  validation_status: "not_validated",
  validation_status_label: "nie sprawdzono w WILQ",
  human_diagnosis: "Merchant Center ma fakty o problemach i próbki produktów do sprawdzenia.",
  recommended_reason: "Przejrzyj podgląd bez mutacji feedu.",
  payload: {
    action_type: "merchant_feed_issue",
    preview_contract: "merchant_feed_issue_review_preview_v1",
    payload_preview: [
      ...Array.from({ length: 4 }, (_, index) => ({
        id: `merchant_feed_issue_review_empty_${index}`,
        preview_contract: "merchant_feed_issue_review_preview_v1",
        operation_type: "MerchantIssueClusterReview",
        issue_type: "landing_page_error",
        issue_type_label: "błąd strony docelowej",
        affected_attribute: "n:link",
        affected_attribute_label: "link produktu",
        metric_snapshot: { issue_product_count: 2 },
        metric_snapshot_labels: { issue_product_count: "zgłoszenia problemów" },
        sample_products_available: false,
        sample_product_ids: [],
        sample_titles: [],
        apply_allowed: false,
        api_mutation_ready: false,
        destructive: false
      })),
      {
        id: "merchant_feed_issue_review_1",
        preview_contract: "merchant_feed_issue_review_preview_v1",
        operation_type: "MerchantIssueClusterReview",
        issue_type: "availability_updated",
        issue_type_label: "zmiana dostępności do sprawdzenia",
        affected_attribute: "n:availability",
        affected_attribute_label: "dostępność",
        metric_snapshot: { issue_product_count: 23 },
        metric_snapshot_labels: { issue_product_count: "zgłoszenia problemów" },
        sample_products_available: true,
        sample_product_ids: ["online~pl~PL~SKU-001", "online~pl~PL~SKU-002"],
        sample_titles: ["Sorbent chemiczny 10 kg"],
        apply_allowed: false,
        api_mutation_ready: false,
        destructive: false
      }
    ]
  },
  preview_cards: [
    {
      id: "merchant_feed_issue_review_1",
      kind: "merchant_feed_issue_review",
      title_label: "Problem feedu do sprawdzenia",
      subtitle_label: "zmiana dostępności do sprawdzenia / dostępność",
      status_label: "zapis zmian zablokowany",
      rows: [
        { label: "Problem", value: "zmiana dostępności do sprawdzenia" },
        { label: "Atrybut", value: "dostępność" },
        { label: "Zgłoszenia", value: "23 zgłoszeń problemu" },
        { label: "Próbki produktów", value: "1 próbka z nazwą produktu" },
        { label: "Tytuły próbek", value: "Sorbent chemiczny 10 kg" }
      ],
      apply_state_label: "zapis zmian zablokowany",
      system_readiness_label: "system zablokowany przed zapisem"
    }
  ],
  review_gate: {
    status: "pending_validation",
    status_label: "czeka na sprawdzenie",
    summary: "Wymaga sprawdzenia w WILQ; zapis zmian pozostaje zablokowany.",
    required_checks: ["validate_action_object", "human_confirm_before_apply"],
    required_check_labels: ["sprawdzenie akcji", "potwierdzenie człowieka przed zapisem"],
    operator_checklist: ["validate_action_object", "human_confirm_before_apply"],
    operator_checklist_labels: ["sprawdzenie akcji", "potwierdzenie człowieka przed zapisem"],
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
    last_confirmation_by: null,
    last_confirmation_at: null,
    last_confirmation_summary: null,
    last_review_outcome: null,
    last_review_outcome_label: null,
    last_reviewed_by: null,
    last_reviewed_at: null,
    last_review_summary: null,
    last_impact_check_status: null,
    last_impact_check_status_label: null,
    last_impact_checked_by: null,
    last_impact_checked_at: null,
    last_impact_check_summary: null,
    last_mutation_audit_id: null,
    last_mutation_audit_status: null,
    last_mutation_audit_status_label: null,
    last_mutation_audit_actor: null,
    last_mutation_audit_at: null,
    last_mutation_audit_summary: null,
    last_mutation_attempted: null,
    last_mutation_adapter: null,
    last_mutation_audit_event_id: null,
    last_mutation_blockers: [],
    last_mutation_blocker_labels: []
  },
  audit_events: []
};

const adsActionFixture: ActionObject = {
  ...actionFixture,
  preview_cards: [
    {
      id: "ads_budget_preview_0",
      kind: "google_ads_budget_review",
      title_label: "Budżet kampanii do sprawdzenia",
      subtitle_label: "ocena budżetu bez zapisu zmian",
      status_label: "zapis zmian zablokowany",
      rows: [
        {
          label: "Kampania",
          value: "(2026) Ekologus Ogólna"
        },
        {
          label: "Budżet",
          value: "(2026) Ekologus Ogólna"
        },
        {
          label: "Obecny budżet",
          value: "10.00 PLN"
        },
        {
          label: "Propozycja",
          value: "brak"
        },
        {
          label: "Bezpieczeństwo",
          value: "zablokowane"
        }
      ],
      apply_state_label: "zapis zmian zablokowany",
      system_readiness_label: "system zablokowany przed zapisem"
    }
  ],
  id: "act_ads",
  title: "Przygotuj kolejkę przeglądu kampanii Google Ads",
  domain: "google_ads",
  connector: "google_ads",
  risk: "medium",
  evidence_ids: ["ev_refresh_google_ads"],
  human_diagnosis: "Google Ads ma kampanie i budżety do sprawdzenia.",
  recommended_reason: "Przejrzyj budżet bez mutacji kampanii.",
  payload: {
    action_type: "campaign_change_review",
    preview_contract: "budget_apply_preview_v1",
    budget_payload_preview: [
      {
        id: "budget_apply_preview_23704710371_15473121355",
        campaign_id: "23704710371",
        campaign_name: "(2026) Ekologus Ogólna",
        campaign_budget_id: "15473121355",
        campaign_budget_name: "(2026) Ekologus Ogólna",
        operation_type: "CampaignBudgetOperation",
        current_budget_amount_micros: 10000000,
        proposed_budget_amount_micros: null,
        proposed_budget_delta_micros: null,
        reason:
          "Podgląd do sprawdzenia CampaignBudgetOperation. Google Ads nie zwrócił recommended budget.",
        evidence_ids: ["ev_refresh_google_ads"],
        required_validation: [
          "review_campaign_activity",
          "human_budget_goal",
          "campaign_budget_apply_safety"
        ],
        blocked_claims: ["skalowanie budżetu", "zmiana budżetu", "zmarnowany budżet"],
        safety_review: {
          safety_contract: "campaign_budget_apply_safety_v1",
          status: "blocked",
          status_label: "zablokowane",
          reason: "Zapis zmiany budżetu zablokowany: brak proponowanej kwoty.",
          missing_requirements: ["human_budget_goal", "recommended_budget_missing"],
          apply_allowed: false,
          api_mutation_ready: false,
          destructive: false
        },
        api_mutation_ready: false,
        apply_allowed: false,
        destructive: false
      }
    ]
  }
};

const adsRecommendationActionFixture: ActionObject = {
  ...actionFixture,
  preview_cards: [
    {
      id: "recommendation_apply_preview_display",
      kind: "google_ads_recommendation_review",
      title_label: "Rekomendacja Google Ads do sprawdzenia",
      subtitle_label: "ocena rekomendacji bez zapisu zmian",
      status_label: "zapis zmian zablokowany",
      rows: [
        {
          label: "Typ rekomendacji",
          value: "rozszerzenie kampanii na sieć reklamową"
        },
        {
          label: "Kampania",
          value: "powiązana kampania do sprawdzenia"
        },
        {
          label: "Budżet kampanii",
          value: "powiązany budżet do sprawdzenia"
        },
        {
          label: "Warunki sprawdzenia",
          value:
            "sprawdź typ rekomendacji, sprawdź metryki wpływu, sprawdź historię zmian, sprawdź cel biznesowy"
        },
        {
          label: "Czego nie wolno twierdzić",
          value: "zapis rekomendacji, automatyczne przyjęcie rekomendacji, obietnica poprawy wyniku"
        }
      ],
      apply_state_label: "zapis zmian zablokowany",
      system_readiness_label: "system zablokowany przed zapisem"
    }
  ],
  id: "act_ads_recommendation",
  title: "Przygotuj ocenę rekomendacji Google Ads",
  domain: "google_ads",
  connector: "google_ads",
  risk: "medium",
  evidence_ids: ["ev_refresh_google_ads"],
  human_diagnosis: "Google Ads ma rekomendacje do sprawdzenia, ale zapis zmian jest zablokowany.",
  recommended_reason: "Przejrzyj typ rekomendacji bez akceptowania jej w Google Ads.",
  payload: {
    action_type: "google_ads_recommendation_review",
    preview_contract: "recommendation_apply_preview_v1",
    payload_preview: [
      {
        id: "recommendation_apply_preview_display",
        recommendation_type: "DISPLAY_EXPANSION_OPT_IN",
        recommendation_type_label: "rozszerzenie kampanii na sieć reklamową",
        campaign_id: "23848569273",
        campaign_budget_id: "15587163334",
        operation_type: "ApplyRecommendationOperation",
        required_validation: [
          "review_recommendation_type",
          "review_impact_metrics",
          "review_change_history",
          "review_business_goal"
        ],
        required_validation_labels: [
          "sprawdź typ rekomendacji",
          "sprawdź metryki wpływu",
          "sprawdź historię zmian",
          "sprawdź cel biznesowy"
        ],
        blocked_claims: [
          "zapis rekomendacji",
          "automatyczne przyjęcie rekomendacji",
          "obietnica poprawy wyniku"
        ],
        api_mutation_ready: false,
        apply_allowed: false,
        destructive: false
      }
    ]
  }
};

const customSegmentActionFixture: ActionObject = {
  ...actionFixture,
  preview_cards: [
    {
      id: "ads_custom_segment_preview_0",
      kind: "google_ads_custom_segment_review",
      title_label: "Segment odbiorców do sprawdzenia",
      subtitle_label: "ocena segmentu bez zapisu zmian",
      status_label: "zapis zmian zablokowany",
      rows: [
        {
          label: "Nazwa",
          value: "Segment z wyszukiwanych haseł"
        },
        {
          label: "Typ odbiorców",
          value: "słowa kluczowe"
        },
        {
          label: "Hasła źródłowe",
          value: "alba czeladź, asekol pl organizacja odzysku sprzętu elektrycznego i elektronicznego s a, bdo szkolenia stacjonarne"
        },
        {
          label: "Kampania do sprawdzenia",
          value: "Kompendium PPWR"
        },
        {
          label: "Bezpieczeństwo",
          value: "zablokowane"
        },
        {
          label: "Braki",
          value: "prognoza albo rozmiar odbiorców, wzbogacenie danych przez Keyword Planner"
        }
      ],
      apply_state_label: "zapis zmian zablokowany",
      system_readiness_label: "system zablokowany przed zapisem"
    }
  ],
  id: "act_custom_segments",
  title: "Przygotuj propozycje segmentów z wyszukiwanych haseł",
  domain: "google_ads",
  connector: "google_ads",
  risk: "medium",
  evidence_ids: ["ev_refresh_google_ads"],
  human_diagnosis: "Search terms mogą zasilić segment odbiorców do sprawdzenia.",
  recommended_reason: "Przejrzyj źródłowe hasła i kontrolę bezpieczeństwa przed kierowaniem reklam.",
  payload: {
    action_type: "custom_segment_review",
    preview_contract: "custom_segment_change_preview_v1",
    payload_preview: [
      {
        id: "custom_segment_preview_google_ads_search_terms",
        custom_segment_name: "Segment z wyszukiwanych haseł",
        member_type: "KEYWORD",
        member_type_label: "słowa kluczowe",
        source_terms: [
          "alba czeladź",
          "asekol pl organizacja odzysku sprzętu elektrycznego i elektronicznego s a",
          "bdo szkolenia stacjonarne"
        ],
        required_validation: [
          "review_source_terms",
          "reject_brand_or_low_intent_terms",
          "keyword_planner_enrichment",
          "forecast_or_audience_size"
        ],
        required_validation_labels: [
          "sprawdź źródłowe hasła",
          "odrzuć brandowe lub niskointencyjne frazy",
          "wzbogać dane przez Keyword Planner",
          "sprawdź prognozę albo wielkość odbiorców"
        ],
        blocked_claims: ["rozmiar odbiorców", "wzrost konwersji", "zapis kierowania reklam"],
        targeting_preview: [
          {
            campaign_id: "23848569273",
            campaign_name: "Kompendium PPWR",
            operation_type: "custom_segment_targeting_review",
            apply_allowed: false,
            api_mutation_ready: false
          }
        ],
        safety_review: {
          status: "blocked",
          status_label: "zablokowane",
          reason: "Zapis segmentu niestandardowego zablokowany.",
          missing_requirements: ["forecast_or_audience_size", "keyword_planner_enrichment"],
          missing_requirement_labels: [
            "prognoza albo rozmiar odbiorców",
            "wzbogacenie danych przez Keyword Planner"
          ]
        },
        api_mutation_ready: false,
        apply_allowed: false,
        destructive: false
      }
    ]
  }
};

const negativeKeywordActionFixture: ActionObject = {
  ...actionFixture,
  preview_cards: [
    {
      id: "ads_negative_keyword_preview_0",
      kind: "google_ads_negative_keyword_review",
      title_label: "Wykluczenie słowa do sprawdzenia",
      subtitle_label: "ocena intencji zapytania bez zapisu zmian",
      status_label: "zapis zmian zablokowany",
      rows: [
        {
          label: "Hasło",
          value: "alba czeladź"
        },
        {
          label: "Wykluczenie",
          value: "alba czeladź"
        },
        {
          label: "Dopasowanie",
          value: "dopasowanie ścisłe"
        },
        {
          label: "Poziom",
          value: "grupa reklam"
        },
        {
          label: "Kampania",
          value: "Kompendium PPWR"
        },
        {
          label: "Grupa reklam",
          value: "Grupa reklam 1"
        }
      ],
      apply_state_label: "zapis zmian zablokowany",
      system_readiness_label: "system zablokowany przed zapisem"
    }
  ],
  id: "act_negative_keywords",
  title: "Przygotuj kolejkę oceny wykluczeń z wyszukiwanych haseł",
  domain: "google_ads",
  connector: "google_ads",
  risk: "medium",
  evidence_ids: ["ev_refresh_google_ads"],
  human_diagnosis: "Search terms mogą wymagać sprawdzenia wykluczeń, ale zapis zmian jest zablokowany.",
  recommended_reason: "Przejrzyj kontekst wyszukiwanego hasła i safety przed wykluczeniem.",
  payload: {
    action_type: "negative_keyword_review",
    preview_contract: "negative_keyword_change_preview_v1",
    payload_preview: [
      {
        id: "negative_keyword_preview_23848569273_alba",
        search_term: "alba czeladź",
        negative_keyword_text: "alba czeladź",
        match_type: "EXACT",
        match_type_label: "dopasowanie ścisłe",
        level: "ad_group",
        level_label: "grupa reklam",
        campaign_id: "23848569273",
        campaign_name: "Kompendium PPWR",
        ad_group_id: "203360679544",
        ad_group_name: "Grupa reklam 1",
        required_validation: [
          "review_search_term_context",
          "check_existing_keywords_and_match_types",
          "90_day_safety_check",
          "human_confirm_before_apply"
        ],
        required_validation_labels: [
          "sprawdzenie intencji zapytania",
          "sprawdź istniejące słowa kluczowe i dopasowania",
          "sprawdź bezpieczeństwo z 90 dni",
          "potwierdzenie człowieka przed zapisem"
        ],
        blocked_claims: ["dodanie wykluczających słów kluczowych", "marnowanie budżetu na zapytaniach", "CPA", "zwrot z reklam"],
        api_mutation_ready: false,
        apply_allowed: false,
        destructive: false
      }
    ]
  }
};

const ngramActionFixture: ActionObject = {
  ...actionFixture,
  preview_cards: [
    {
      id: "search_term_ngram_review_asekol_1",
      kind: "google_ads_search_term_ngram_review",
      title_label: "Temat zapytań do sprawdzenia",
      subtitle_label: "ocena intencji zapytań bez zapisu zmian",
      status_label: "zapis zmian zablokowany",
      rows: [
        { label: "Temat", value: "asekol" },
        { label: "Rozmiar", value: "1" },
        { label: "Zapytania użytkowników", value: "1" },
        {
          label: "Przykłady",
          value: "asekol pl organizacja odzysku sprzętu elektrycznego i elektronicznego s a"
        },
        { label: "Kliknięcia", value: "1" },
        { label: "Wyświetlenia", value: "1" },
        { label: "Koszt", value: "24.17 PLN" },
        { label: "Konwersje", value: "0" },
        { label: "Braki", value: "ręczna ocena intencji" },
        {
          label: "Czego nie wolno twierdzić",
          value: "marnowanie budżetu na zapytaniach, dodanie wykluczających słów kluczowych, CPA, zwrot z reklam"
        }
      ],
      apply_state_label: "zapis zmian zablokowany",
      system_readiness_label: "system zablokowany przed zapisem"
    }
  ],
  id: "act_ngrams",
  title: "Przygotuj ocenę tematów z n-gramów wyszukiwanych haseł",
  domain: "google_ads",
  connector: "google_ads",
  risk: "medium",
  evidence_ids: ["ev_refresh_google_ads"],
  human_diagnosis: "Search terms mają n-gramy do sprawdzenia intencji.",
  recommended_reason: "Przejrzyj tematy zanim powstanie podgląd dodania wykluczających słów kluczowych.",
  payload: {
    action_type: "google_ads_search_term_ngram_review",
    preview_contract: "search_term_ngram_review_v1",
    ngram_preview: [
      {
        id: "search_term_ngram_review_asekol_1",
        ngram: "asekol",
        ngram_size: 1,
        source_search_term_count: 1,
        sample_search_terms: [
          "asekol pl organizacja odzysku sprzętu elektrycznego i elektronicznego s a"
        ],
        clicks: 1,
        impressions: 1,
        cost_micros: 24173334,
        conversions: 0,
        conversion_value: 0,
        operation_type: "SearchTermNgramReview",
        missing_read_contracts: [
          "human_intent_review",
          "ngram_to_negative_keyword_change_preview"
        ],
        missing_read_contract_labels: [
          "ręczna ocena intencji",
          "podgląd przejścia z tematu zapytań do wykluczenia"
        ],
        required_validation: [
          "review_ngram_intent",
          "review_source_search_terms",
          "compare_90_day_safety_read"
        ],
        required_validation_labels: [
          "sprawdź intencję tematu zapytań",
          "sprawdź źródłowe wyszukiwane hasła",
          "porównaj z 90-dniową kontrolą bezpieczeństwa"
        ],
        blocked_claims: ["marnowanie budżetu na zapytaniach", "dodanie wykluczających słów kluczowych", "CPA", "zwrot z reklam"],
        api_mutation_ready: false,
        apply_allowed: false,
        destructive: false
      }
    ]
  }
};

const demandGenActionFixture: ActionObject = {
  ...actionFixture,
  preview_cards: [
    {
      id: "demand_gen_readiness_preview_0",
      kind: "google_ads_demand_gen_readiness_review",
      title_label: "Gotowość Demand Gen do sprawdzenia",
      subtitle_label: "ocena gotowości bez zapisu zmian",
      status_label: "zapis zmian zablokowany",
      rows: [
        {
          label: "Kampanie ocenione",
          value: "20"
        },
        {
          label: "Kanały kampanii",
          value: "PMax: 8, Search: 10, nieznany kanał: 2"
        },
        {
          label: "Kampanie Demand Gen",
          value: "0"
        },
        {
          label: "Kreacje i zasoby",
          value: "0"
        },
        {
          label: "Braki",
          value: "jakość stron wejścia Demand Gen według kampanii, ograniczenia przejścia na Demand Gen"
        }
      ],
      apply_state_label: "zapis zmian zablokowany",
      system_readiness_label: "system zablokowany przed zapisem"
    }
  ],
  id: "act_demand_gen",
  title: "Przygotuj sprawdzenie gotowości Demand Gen",
  domain: "google_ads",
  connector: "google_ads",
  risk: "medium",
  evidence_ids: ["ev_refresh_google_ads", "ev_refresh_ga4"],
  human_diagnosis: "Demand Gen wymaga przeglądu gotowości przed launchem albo przejściem kampanii.",
  recommended_reason: "Sprawdź kanały Ads, brakujące kontrakty i blokady apply.",
  payload: {
    action_type: "demand_gen_readiness_review",
    preview_contract: "demand_gen_readiness_review_preview_v1",
    payload_preview: [
      {
        id: "demand_gen_readiness_review",
        preview_contract: "demand_gen_readiness_review_preview_v1",
        operation_type: "DemandGenReadinessReview",
        campaign_rows_evaluated: 20,
        campaign_channel_counts: {
          PERFORMANCE_MAX: 8,
          SEARCH: 10,
          UNKNOWN: 2
        },
        demand_gen_campaign_row_count: 0,
        demand_gen_ad_group_ad_row_count: 0,
        demand_gen_creative_asset_row_count: 0,
        demand_gen_landing_quality_row_count: 0,
        missing_read_contracts: [
          "demand_gen_landing_quality_by_campaign",
          "demand_gen_transition_constraints"
        ],
        missing_read_contract_labels: [
          "jakość stron wejścia Demand Gen według kampanii",
          "ograniczenia przejścia na Demand Gen"
        ],
        required_validation: [
          "review_ads_campaign_channel_context",
          "review_ga4_landing_source_campaign_context",
          "review_demand_gen_missing_contracts"
        ],
        required_validation_labels: [
          "sprawdź kanały kampanii Ads",
          "sprawdź stronę wejścia, źródło i kampanię w GA4",
          "sprawdź braki danych Demand Gen"
        ],
        blocked_claims: [
          "rekomendacja uruchomienia Demand Gen",
          "gotowość przejścia na Demand Gen",
          "ocena jakości kreacji",
          "wzrost skuteczności"
        ],
        api_mutation_ready: false,
        apply_allowed: false,
        destructive: false
      }
    ]
  }
};

const ga4TrackingActionFixture: ActionObject = {
  ...actionFixture,
  preview_cards: [],
  id: "act_ga4_tracking",
  title: "Sprawdź jakość pomiaru GA4 przed oceną kampanii",
  domain: "ga4",
  connector: "google_analytics_4",
  risk: "low",
  evidence_ids: ["ev_refresh_ga4"],
  human_diagnosis: "GA4 ma wiersze strony wejścia, źródła ruchu i kampanii do sprawdzenia jakości pomiaru.",
  recommended_reason: "Sprawdź dopasowanie komunikatu i powiązanie konwersji bez obietnic zwrotu z reklam.",
  payload: {
    action_type: "ga4_tracking_gap",
    preview_contract: "ga4_tracking_quality_review_v1",
    payload_preview: [
      {
        id: "ga4_tracking_review_1",
        preview_contract: "ga4_tracking_quality_review_v1",
        operation_type: "tracking_quality_review",
        landing_page: "/",
        source_medium: "google / cpc",
        campaign_name: "(2026) Ekologus Ogólna",
        tracking_dimension_gaps: [],
        metric_snapshot: {
          active_users: 49,
          engagement_rate: 0.766234,
          event_count: 1190,
          screen_page_views: 392,
          sessions: 77
        },
        metric_snapshot_labels: {
          active_users: "aktywni użytkownicy",
          engagement_rate: "zaangażowanie",
          event_count: "zdarzenia",
          screen_page_views: "odsłony",
          sessions: "sesje"
        },
        reason:
          "Lista sprawdzenia strony wejścia, źródła ruchu i kampanii do oceny jakości ruchu. To pozwala sprawdzić dopasowanie komunikatu, ale nie odblokowuje obietnic zwrotu z reklam ani przychodu.",
        required_validation: [
          "review_landing_page_dimension",
          "review_source_medium_dimension",
          "review_campaign_name_dimension",
          "review_conversion_or_key_event_mapping"
        ],
        required_validation_labels: [
          "sprawdź stronę wejścia",
          "sprawdź źródło i medium ruchu",
          "sprawdź nazwę kampanii",
          "sprawdź powiązanie konwersji albo zdarzenia kluczowego"
        ],
        blocked_claims: ["współczynnik konwersji", "zwrot z reklam", "przychód", "naprawiony pomiar"],
        api_mutation_ready: false,
        apply_allowed: false,
        destructive: false
      }
    ]
  }
};

const localoActionFixture: ActionObject = {
  ...actionFixture,
  preview_cards: [],
  id: "act_localo",
  title: "Przygotuj sprawdzenie widoczności lokalnej Localo",
  domain: "localo",
  connector: "localo",
  risk: "medium",
  evidence_ids: ["ev_refresh_localo"],
  human_diagnosis: "Localo ma fakty zbiorcze do sprawdzenia lokalnej widoczności.",
  recommended_reason: "Przejrzyj metryki Localo bez claimów GBP i konkurencji.",
  payload: {
    action_type: "local_visibility_task",
    preview_contract: "local_visibility_review_preview_v1",
    payload_preview: [
      {
        id: "localo_visibility_review",
        preview_contract: "local_visibility_review_preview_v1",
        operation_type: "local_visibility_review",
        metric_snapshot: {
          localo_avg_latest_grid_position: 3.2632,
          localo_avg_visibility_change: 0.6957,
          localo_avg_visibility_current: 53.1739,
          localo_tracked_keyword_count: 23,
          localo_active_place_count: 4,
          localo_avg_rating: 4.75,
          localo_review_reply_rate: 0.813283,
          localo_reviews_count: 798,
          localo_read_contract_count: 3
        },
        allowed_contracts: ["local_rankings", "place_inventory", "reviews"],
        allowed_contract_labels: ["lokalne pozycje", "lista lokalizacji", "opinie"],
        missing_read_contracts: ["gbp_visibility", "competitor_visibility", "local_tasks"],
        missing_read_contract_labels: [
          "widoczność Google Business Profile",
          "widoczność konkurencji",
          "lokalne zadania do wykonania"
        ],
        required_validation: [
          "review_place_inventory",
          "review_local_rankings_aggregate",
          "review_reviews_aggregate"
        ],
        required_validation_labels: [
          "sprawdź listę lokalizacji",
          "sprawdź zbiorcze dane lokalnych pozycji",
          "sprawdź zbiorcze dane opinii"
        ],
        blocked_claims: [
          "wyniki profilu firmy w Google",
          "widoczność konkurencji",
          "poprawa widoczności lokalnej"
        ],
        api_mutation_ready: false,
        apply_allowed: false,
        destructive: false
      }
    ]
  }
};

const socialDraftActionFixture: ActionObject = {
  ...actionFixture,
  preview_cards: [
    {
      id: "social_draft_input_0",
      kind: "social_draft_input_review",
      title_label: "Materiał do posta do sprawdzenia",
      subtitle_label: "LinkedIn: źródło do szkicu bez publikacji",
      status_label: "publikacja zablokowana",
      rows: [
        {
          label: "Źródło danych",
          value: "Google Search Console"
        },
        {
          label: "Sygnał",
          value: "kliknięcia"
        },
        {
          label: "Wartość",
          value: "12"
        },
        {
          label: "Kontekst",
          value: "sygnał z Google Search Console"
        },
        {
          label: "Ograniczenia",
          value: "użyj tylko dowodów z WILQ, pisz po polsku"
        },
        {
          label: "Czego nie wolno twierdzić",
          value: "zwrot z reklam, przychód"
        }
      ],
      apply_state_label: "zapis zmian zablokowany",
      system_readiness_label: "wymaga sprawdzenia przez człowieka"
    },
    {
      id: "social_draft_input_1",
      kind: "social_draft_input_review",
      title_label: "Materiał do posta do sprawdzenia",
      subtitle_label: "LinkedIn: źródło do szkicu bez publikacji",
      status_label: "publikacja zablokowana",
      rows: [
        {
          label: "Źródło danych",
          value: "Merchant Center"
        },
        {
          label: "Sygnał",
          value: "zgłoszenia problemów"
        },
        {
          label: "Wartość",
          value: "14"
        },
        {
          label: "Kontekst",
          value: "zgłoszenie problemu danych produktowych Merchant Center"
        }
      ],
      apply_state_label: "zapis zmian zablokowany",
      system_readiness_label: "wymaga sprawdzenia przez człowieka"
    }
  ],
  id: "act_social_draft",
  title: "Przygotuj propozycje postów LinkedIn z dowodów WILQ",
  domain: "social",
  connector: "linkedin",
  risk: "medium",
  evidence_ids: ["ev_refresh_gsc", "ev_refresh_merchant"],
  human_diagnosis: "WILQ ma dowody, z których można przygotować materiał social do sprawdzenia.",
  recommended_reason: "Przejrzyj źródłowe metryki i blokady zanim powstanie szkic.",
  payload: {
    action_type: "linkedin_post_candidate",
    mode: "prepare_only",
    connector: "linkedin",
    source_inputs: [
      {
        source_connector: "google_search_console",
        metric_name: "clicks",
        value: 12,
        context_summary: "sygnał z Google Search Console",
        evidence_id: "ev_refresh_gsc"
      },
      {
        source_connector: "google_merchant_center",
        metric_name: "issue_product_count",
        value: 14,
        context_summary: "zgłoszenie problemu danych produktowych Merchant Center",
        evidence_id: "ev_refresh_merchant"
      }
    ],
    draft_constraints: [
      "use_only_wilq_evidence",
      "write_in_polish",
      "no_performance_claims_without_source_metric",
      "require_human_review_before_apply"
    ],
    draft_constraint_labels: [
      "użyj tylko dowodów z WILQ",
      "pisz po polsku",
      "bez obietnic skuteczności bez metryk źródłowych",
      "człowiek sprawdza przed zapisem"
    ],
    blocked_claims: ["zwrot z reklam", "przychód", "wzrost konwersji", "wdrożona poprawka produktu"],
    destructive: false
  }
};

const keywordPlannerAccessActionFixture: ActionObject = {
  ...actionFixture,
  preview_cards: [
    {
      id: "keyword_planner_access_preview",
      kind: "google_ads_keyword_planner_access_review",
      title_label: "Dostęp do Keyword Plannera do odblokowania",
      subtitle_label: "blokada dostępu bez zapisu zmian",
      status_label: "zapis zmian zablokowany",
      rows: [
        {
          label: "Zablokowany dostęp",
          value: "Keyword Planner"
        },
        {
          label: "Powód",
          value: "token deweloperski nie ma zatwierdzonego dostępu do Keyword Plannera"
        },
        {
          label: "Wymagany stan",
          value: "token deweloperski zatwierdzony dla Keyword Plannera, Keyword Planner może generować propozycje"
        }
      ],
      apply_state_label: "zapis zmian zablokowany",
      system_readiness_label: "wymaga zmiany po stronie Google Ads"
    }
  ],
  id: "act_keyword_planner_access",
  title: "Odblokuj Keyword Planner dla Google Ads",
  domain: "google_ads",
  connector: "google_ads",
  risk: "medium",
  evidence_ids: ["ev_connector_google_ads_status", "ev_refresh_google_ads"],
  human_diagnosis: "Keyword Planner jest zablokowany przez stan tokena deweloperskiego.",
  recommended_reason: "Odblokuj dostęp zanim WILQ zacznie oceniać prognozy i rozmiar odbiorców.",
  payload: {
    action_type: "configure_google_ads_keyword_planner_access",
    connector: "google_ads",
    mode: "prepare_only",
    blocked_api: "Keyword Planner",
    blocked_reason:
      "api_code=403, api_status=PERMISSION_DENIED, ads_error=authorizationError.DEVELOPER_TOKEN_NOT_APPROVED 403",
    required_google_ads_state: [
      "developer_token_approved_for_keyword_planner",
      "keyword_planner_generate_ideas_allowed"
    ],
    required_google_ads_state_labels: [
      "token deweloperski zatwierdzony dla Keyword Plannera",
      "Keyword Planner może generować propozycje"
    ],
    helper_steps: [
      "Sprawdź status tokena deweloperskiego Google Ads API w Google Ads API Center.",
      "Po zmianie statusu wykonaj odczyt danych Google Ads."
    ],
    required_validation: [
      "confirm_developer_token_approval",
      "rerun_google_ads_data_read",
      "verify_keyword_planner_idea_rows",
      "human_confirm_before_apply"
    ],
    required_validation_labels: [
      "potwierdź akceptację tokena deweloperskiego",
      "uruchom ponowny odczyt Google Ads",
      "sprawdź wiersze Keyword Planner",
      "potwierdzenie człowieka przed zapisem"
    ],
    blocked_claims: ["rozmiar odbiorców", "prognoza", "wzrost konwersji", "zwrot z reklam"],
    apply_allowed: false,
    destructive: false
  }
};

const adsTargetGuardrailActionFixture: ActionObject = {
  ...actionFixture,
  preview_cards: [],
  id: "act_ads_target_guardrails",
  title: "Potwierdź docelowy zwrot z reklam albo koszt pozyskania celu dla Ads",
  domain: "google_ads",
  connector: "google_ads",
  risk: "medium",
  evidence_ids: ["ev_connector_google_ads_status", "ev_refresh_google_ads"],
  human_diagnosis: "WILQ ma fakty Ads, ale docelowy zwrot z reklam albo koszt pozyskania celu wymaga potwierdzenia operatora.",
  recommended_reason: "Potwierdź cel zanim WILQ nazwie kampanie opłacalnymi albo nieopłacalnymi.",
  payload: {
    action_type: "confirm_ads_target_guardrails",
    connector: "google_ads",
    mode: "prepare_only",
    credential_source: "repo_env",
    current_context: {
      profit_margin: 0.3,
      business_goal: "wstępny review jakości leadów i kosztu pozyskania dla Ekologus",
      budget_goal: "wstępnie chronić obecny budżet; eskalować tylko po review",
      target_roas: null,
      target_cpa_micros: null,
      configured_sources: [
        "WILQ_ADS_PROFIT_MARGIN",
        "WILQ_ADS_BUSINESS_GOAL",
        "WILQ_ADS_BUDGET_GOAL"
      ],
      target_confirmation_id: null
    },
    target_env_options: {
      target_roas_or_cpa: ["WILQ_ADS_TARGET_ROAS", "WILQ_ADS_TARGET_CPA_MICROS"],
      target_roas_or_cpa_labels: [
        "docelowy zwrot z reklam",
        "docelowy koszt pozyskania celu"
      ]
    },
    missing_read_contracts: ["target_roas_or_cpa", "human_strategy_review"],
    missing_read_contract_labels: [
      "docelowy zwrot z reklam albo koszt pozyskania celu",
      "człowiek sprawdza strategię"
    ],
    required_validation: [
      "review_profit_margin_model",
      "review_business_goal",
      "review_human_budget_goal",
      "confirm_target_roas_or_cpa",
      "human_strategy_review"
    ],
    required_validation_labels: [
      "sprawdź model marży",
      "sprawdź cel biznesowy",
      "sprawdź cel budżetu od człowieka",
      "potwierdź docelowy zwrot albo koszt pozyskania celu",
      "człowiek sprawdza strategię"
    ],
    allowed_uses_after_confirmation: [
      "target_metrics_review",
      "campaign_review_context",
      "budget_review_context"
    ],
    allowed_uses_after_confirmation_labels: [
      "przegląd wskaźników względem celu",
      "kontekst przeglądu kampanii",
      "kontekst przeglądu budżetu"
    ],
    blocked_claims: [
      "ocena KPI względem celu przed potwierdzeniem",
      "ocena opłacalności",
      "skalowanie budżetu",
      "zmiana budżetu",
      "zapis rekomendacji"
    ],
    apply_allowed: false,
    destructive: false
  }
};

const adsStrategyReviewActionFixture: ActionObject = {
  ...actionFixture,
  preview_cards: [],
  id: "act_ads_strategy_review",
  title: "Zapisz ocenę strategii Ads przez człowieka",
  domain: "google_ads",
  connector: "google_ads",
  risk: "medium",
  evidence_ids: ["ev_connector_google_ads_status", "ev_refresh_google_ads"],
  human_diagnosis: "WILQ ma Ads facts, ale strategia wymaga review człowieka.",
  recommended_reason: "Zapisz ocenę strategii zanim WILQ przejdzie do decyzji budżetowych.",
  payload: {
    action_type: "record_ads_strategy_review",
    connector: "google_ads",
    mode: "prepare_only",
    current_context: {
      profit_margin: 0.3,
      business_goal: "wstępny review jakości leadów i kosztu pozyskania dla Ekologus",
      budget_goal: "wstępnie chronić obecny budżet; eskalować tylko po review",
      target_roas: null,
      target_cpa_micros: null,
      configured_sources: [
        "WILQ_ADS_PROFIT_MARGIN",
        "WILQ_ADS_BUSINESS_GOAL",
        "WILQ_ADS_BUDGET_GOAL"
      ]
    },
    latest_strategy_review: null,
    operator_review_gates: [
      "human_strategy_review",
      "review_profit_margin_model",
      "review_business_goal",
      "review_human_budget_goal",
      "review_target_fit"
    ],
    operator_review_gate_labels: [
      "człowiek sprawdza strategię",
      "sprawdź model marży",
      "sprawdź cel biznesowy",
      "sprawdź cel budżetu od człowieka",
      "sprawdź dopasowanie do celu"
    ],
    required_validation: [
      "review_profit_margin_model",
      "review_business_goal",
      "review_human_budget_goal",
      "review_target_fit",
      "record_human_strategy_review_outcome"
    ],
    required_validation_labels: [
      "sprawdź model marży",
      "sprawdź cel biznesowy",
      "sprawdź cel budżetu od człowieka",
      "sprawdź dopasowanie do celu",
      "zapisz wynik sprawdzenia strategii przez człowieka"
    ],
    blocked_claims: [
      "ocena opłacalności",
      "skalowanie budżetu",
      "zmiana budżetu",
      "zapis rekomendacji",
      "automatyczna optymalizacja"
    ],
    apply_allowed: false,
    destructive: false
  }
};

const contentActionFixture: ActionObject = {
  ...actionFixture,
  preview_cards: [
    {
      id: "content_brief_preview_0",
      kind: "content_brief_review",
      title_label: "Plan treści do sprawdzenia",
      subtitle_label: "brief bez pisania i bez publikacji",
      status_label: "zapis zmian zablokowany",
      rows: [
        { label: "Temat", value: "bdo co to" },
        { label: "Tryb", value: "sprawdzić spis treści" },
        {
          label: "URL publiczny",
          value: "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/"
        },
        {
          label: "Opcje",
          value: "odśwież istniejącą treść, scal z istniejącą treścią, zablokuj"
        },
        {
          label: "Cel planu treści",
          value:
            "Sprawdź spis treści i duplikaty przed planem treści dla `bdo co to`. Bez potwierdzenia URL nie twórz nowej strony."
        },
        {
          label: "Kąt treści",
          value:
            "Najpierw potwierdź kanoniczną stronę BDO, potem przygotuj plan treści bez obietnic pozycji."
        },
        { label: "H1", value: "H1 ma jasno odpowiedzieć na intencję `bdo co to`." },
        {
          label: "Brakujące dowody",
          value: "brak potwierdzonego kanonicznego URL w WordPress"
        },
        {
          label: "Warunki sprawdzenia",
          value:
            "istniejący URL potwierdzony w WordPress, kontrola duplikacji i kanibalizacji, potwierdzenie człowieka przed zapisem WordPress"
        }
      ],
      apply_state_label: "zapis zmian zablokowany",
      system_readiness_label: "system zablokowany przed zapisem"
    },
    {
      id: "wordpress_draft_payload_preview_0",
      kind: "wordpress_draft_payload_review",
      title_label: "Szkic WordPress do sprawdzenia",
      subtitle_label: "szkic bez publikacji",
      status_label: "zapis zmian zablokowany",
      rows: [
        { label: "Temat", value: "bdo co to" },
        { label: "Status wpisu", value: "szkic" },
        { label: "Tytuł szkicu", value: "Odświeżenie: zielony ład" },
        {
          label: "Kontrole treści",
          value:
            "spis treści: spis potwierdzony na obecnej stronie, URL kanoniczny: obecny URL potwierdzony, duplikaty: odśwież albo scal zamiast pisać od nowa"
        },
        {
          label: "Szkic WordPress",
          value: "status: zablokowany do przejścia kontroli szkicu"
        }
      ],
      apply_state_label: "zapis zmian zablokowany",
      system_readiness_label: "system zablokowany przed zapisem"
    }
  ],
  id: "act_content",
  title: "Przygotuj kolejkę odświeżenia treści ekologus.pl",
  domain: "content",
  connector: "wordpress_ekologus",
  risk: "medium",
  evidence_ids: ["ev_refresh_gsc"],
  human_diagnosis: "GSC i WordPress wskazują treści do sprawdzenia.",
  recommended_reason: "Przejrzyj plan treści i podgląd szkicu bez publikacji.",
  payload: {
    action_type: "content_refresh_queue",
    preview_contract: "content_brief_preview_v1",
    content_brief_preview: [
      {
        preview_contract: "content_brief_preview_v1",
        candidate_id: "content_brief_gsc_bdo",
        source_type: "gsc_query_page",
        mode: "inventory_check",
        mode_label: "sprawdzić spis treści",
        topic: "bdo co to",
        target_url: "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/",
        wordpress_inventory_match: "missing",
        decision_option_labels: [
          "odśwież istniejącą treść",
          "scal z istniejącą treścią",
          "zablokuj"
        ],
        metric_snapshot: {
          queries: 1,
          clicks: 4,
          impressions: 4429,
          ctr: 0.0009031384059607134,
          average_position: 9.441183111311808
        },
        brief_goal:
          "Sprawdź spis treści i duplikaty przed planem treści dla `bdo co to`. Bez potwierdzenia URL nie twórz nowej strony.",
        content_angle:
          "Najpierw potwierdź kanoniczną stronę BDO, potem przygotuj plan treści bez obietnic pozycji.",
        audience: "Przedsiębiorca sprawdzający obowiązki BDO.",
        key_objections: ["czy istnieje już kanoniczny URL", "czy intencja wymaga checklisty"],
        h1_direction: "H1 ma jasno odpowiedzieć na intencję `bdo co to`.",
        h2_direction: ["czym jest BDO", "obowiązki przedsiębiorcy", "najczęstsze ryzyka"],
        faq_direction: ["Co to jest BDO?", "Kto musi mieć BDO?"],
        cta_direction: "CTA do konsultacji obowiązków BDO bez obietnicy uniknięcia kar.",
        source_facts: ["GSC page=/bdo-co-musi-wiedziec-przedsiebiorca/", "clicks=4"],
        missing_evidence: ["brak potwierdzonego kanonicznego URL w WordPress"],
        brief_outline: [
          {
            section: "intent",
            instruction: "Opisz intencję użytkownika dla `bdo co to`."
          },
          {
            section: "cta",
            instruction: "Dopasuj CTA do usługi Ekologus."
          }
        ],
        required_validation: [
          "wordpress_inventory_check",
          "duplicate_or_cannibalization_check",
          "human_confirm_before_wordpress_write"
        ],
        required_validation_labels: [
          "istniejący URL potwierdzony w WordPress",
          "kontrola duplikacji i kanibalizacji",
          "potwierdzenie człowieka przed zapisem WordPress"
        ],
        blocked_claims: [
          "wzrost liczby leadów",
          "wpływ na przychód",
          "automatyczna publikacja WordPress"
        ],
        source_connectors: ["google_search_console"],
        evidence_ids: ["ev_refresh_gsc"],
        apply_allowed: false,
        api_mutation_ready: false,
        destructive: false
      },
      ...Array.from({ length: 4 }, (_, index) => ({
        preview_contract: "content_brief_preview_v1",
        candidate_id: `content_brief_extra_${index}`,
        source_type: "gsc_query_page",
        mode: "inventory_check",
        mode_label: "sprawdzić spis treści",
        topic: `temat dodatkowy ${index}`,
        target_url: `https://www.ekologus.pl/extra-${index}/`,
        wordpress_inventory_match: "missing",
        decision_options: ["merge", "create", "block"],
        metric_snapshot: {
          queries: 1,
          clicks: index,
          impressions: 100 + index
        },
        brief_goal: "Dodatkowy plan treści do testu limitu kart.",
        required_validation: ["wordpress_inventory_check"],
        blocked_claims: ["wzrost liczby leadów"],
        source_connectors: ["google_search_console"],
        evidence_ids: ["ev_refresh_gsc"],
        apply_allowed: false,
        api_mutation_ready: false,
        destructive: false
      }))
    ],
    wordpress_draft_payload_preview: [
      {
        preview_contract: "wordpress_draft_payload_preview_v1",
        candidate_id: "content_brief_gsc_bdo",
        operation_type: "prepare_new_content_draft_review",
        post_status: "draft",
        post_status_label: "szkic",
        topic: "bdo co to",
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
          "szkic: wymaga decyzji człowieka",
          "człowiek: brak zatwierdzenia"
        ],
        draft_readiness_review_contract_summary: [
          "wymaga: wynik decyzji człowieka",
          "blokuje: zapis szkicu WordPress"
        ],
        wordpress_draft_handoff_summary: [
          "status: zablokowany do przejścia kontroli szkicu"
        ],
        wordpress_draft_handoff_contract_summary: [
          "warunek: kontrola duplikacji i kanibalizacji",
          "blokuje: publikacja WordPress"
        ],
        post_publication_measurement_summary: [
          "status: zablokowany do publikacji i danych po publikacji"
        ],
        draft_payload: {
          post_status: "draft",
          post_title: "Odświeżenie: zielony ład",
          post_excerpt_direction: "Sprawdź spis treści i duplikaty przed planem treści.",
          content_blocks: []
        },
        required_validation_labels: [
          "operator zatwierdził przygotowanie",
          "istniejący URL potwierdzony w WordPress",
          "potwierdzenie człowieka przed zapisem WordPress"
        ],
        apply_allowed: false,
        api_mutation_ready: false,
        destructive: false
      }
    ]
  }
};

function mockFetch() {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/actions/act_1")) {
        return Promise.resolve(Response.json(actionFixture));
      }
      if (url.endsWith("/api/actions/act_ads")) {
        return Promise.resolve(Response.json(adsActionFixture));
      }
      if (url.endsWith("/api/actions/act_ads_recommendation")) {
        return Promise.resolve(Response.json(adsRecommendationActionFixture));
      }
      if (url.endsWith("/api/actions/act_custom_segments")) {
        return Promise.resolve(Response.json(customSegmentActionFixture));
      }
      if (url.endsWith("/api/actions/act_negative_keywords")) {
        return Promise.resolve(Response.json(negativeKeywordActionFixture));
      }
      if (url.endsWith("/api/actions/act_ngrams")) {
        return Promise.resolve(Response.json(ngramActionFixture));
      }
      if (url.endsWith("/api/actions/act_demand_gen")) {
        return Promise.resolve(Response.json(demandGenActionFixture));
      }
      if (url.endsWith("/api/actions/act_ga4_tracking")) {
        return Promise.resolve(Response.json(ga4TrackingActionFixture));
      }
      if (url.endsWith("/api/actions/act_localo")) {
        return Promise.resolve(Response.json(localoActionFixture));
      }
      if (url.endsWith("/api/actions/act_social_draft")) {
        return Promise.resolve(Response.json(socialDraftActionFixture));
      }
      if (url.endsWith("/api/actions/act_keyword_planner_access")) {
        return Promise.resolve(Response.json(keywordPlannerAccessActionFixture));
      }
      if (url.endsWith("/api/actions/act_ads_target_guardrails")) {
        return Promise.resolve(Response.json(adsTargetGuardrailActionFixture));
      }
      if (url.endsWith("/api/actions/act_ads_strategy_review")) {
        return Promise.resolve(Response.json(adsStrategyReviewActionFixture));
      }
      if (url.endsWith("/api/actions/act_content")) {
        return Promise.resolve(Response.json(contentActionFixture));
      }
      return Promise.resolve(Response.json({}));
    })
  );
}

describe("Action detail route", () => {
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

  function renderActionDetail(actionId = "act_1") {
    return render(
      <App
        appRouter={createWilqRouter({
          initialPath: `/actions/${actionId}`,
          defaultPendingMinMs: 0
        })}
        client={testQueryClient}
      />
    );
  }

  it("renders the selected action detail", async () => {
    renderActionDetail();
    await waitFor(() =>
      expect(screen.getByText("Problem feedu do sprawdzenia")).toBeInTheDocument()
    );
    expect(screen.getByText("zmiana dostępności do sprawdzenia / dostępność")).toBeInTheDocument();
    expect(screen.getByText("Problem: zmiana dostępności do sprawdzenia")).toBeInTheDocument();
    expect(screen.getByText("Atrybut: dostępność")).toBeInTheDocument();
    expect(screen.getByText("Zgłoszenia: 23 zgłoszeń problemu")).toBeInTheDocument();
    expect(screen.getByText("Próbki produktów: 1 próbka z nazwą produktu")).toBeInTheDocument();
    expect(screen.queryByText("Przykładowe produkty")).not.toBeInTheDocument();
    expect(screen.queryByText("online~pl~PL~SKU-001")).not.toBeInTheDocument();
    expect(screen.getByText("Dowody: 1 dowód źródłowy")).toBeInTheDocument();
    expect(screen.queryByText("ev_refresh_merchant_feed")).not.toBeInTheDocument();
    expect(screen.getByText("zmiana dostępności do sprawdzenia / dostępność")).toBeInTheDocument();
    expect(screen.queryByText("availability_updated / n:availability")).not.toBeInTheDocument();
    expect(screen.queryByText(/wymaga etykiety problemu z WILQ/)).not.toBeInTheDocument();
    expect(screen.queryByText(/online~pl~PL~SKU-001/)).not.toBeInTheDocument();
    expect(screen.getAllByText(/Sorbent chemiczny 10 kg/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/zapis zmian zablokowany/).length).toBeGreaterThan(0);
  });

  it("renders Google Ads budget change preview without requiring raw JSON", async () => {
    renderActionDetail("act_ads");
    await waitFor(() =>
      expect(
        screen.getByRole("heading", {
          name: "Przygotuj kolejkę przeglądu kampanii Google Ads"
        })
      ).toBeInTheDocument()
    );
    expect(screen.getByText("Budżet kampanii do sprawdzenia")).toBeInTheDocument();
    expect(screen.getByText("ocena budżetu bez zapisu zmian")).toBeInTheDocument();
    expect(screen.queryByText("CampaignBudgetOperation")).not.toBeInTheDocument();
    expect(screen.getByText(/Kampania: \(2026\) Ekologus Ogólna/)).toBeInTheDocument();
    expect(screen.getByText(/Budżet: \(2026\) Ekologus Ogólna/)).toBeInTheDocument();
    expect(screen.getByText(/Obecny budżet: 10.00 PLN/)).toBeInTheDocument();
    expect(screen.getByText(/Propozycja: brak/)).toBeInTheDocument();
    expect(screen.getByText(/Bezpieczeństwo: zablokowane/)).toBeInTheDocument();
    expect(screen.queryByText(/23704710371/)).not.toBeInTheDocument();
    expect(screen.queryByText(/15473121355/)).not.toBeInTheDocument();
    expect(screen.getAllByText(/Zapis zmian:/).length).toBeGreaterThan(0);
  });

  it("renders Google Ads recommendation change preview without requiring raw JSON", async () => {
    renderActionDetail("act_ads_recommendation");
    await waitFor(() =>
      expect(
        screen.getByRole("heading", {
          name: "Przygotuj ocenę rekomendacji Google Ads"
        })
      ).toBeInTheDocument()
    );
    expect(screen.getByText("Rekomendacja Google Ads do sprawdzenia")).toBeInTheDocument();
    expect(screen.getByText("ocena rekomendacji bez zapisu zmian")).toBeInTheDocument();
    expect(screen.queryByText("ApplyRecommendationOperation")).not.toBeInTheDocument();
    expect(
      screen.getByText(/Typ rekomendacji: rozszerzenie kampanii na sieć reklamową/)
    ).toBeInTheDocument();
    expect(screen.getByText(/Kampania: powiązana kampania do sprawdzenia/)).toBeInTheDocument();
    expect(
      screen.getByText(/Budżet kampanii: powiązany budżet do sprawdzenia/)
    ).toBeInTheDocument();
    expect(screen.queryByText(/DISPLAY_EXPANSION_OPT_IN/)).not.toBeInTheDocument();
    expect(screen.queryByText(/23848569273/)).not.toBeInTheDocument();
    expect(screen.queryByText(/15587163334/)).not.toBeInTheDocument();
    expect(screen.getByText(/Warunki sprawdzenia: sprawdź typ rekomendacji/)).toBeInTheDocument();
    expect(screen.getByText(/Czego nie wolno twierdzić: zapis rekomendacji/)).toBeInTheDocument();
    expect(screen.getAllByText(/Zapis zmian:/).length).toBeGreaterThan(0);
  });

  it("renders custom segment change preview without requiring raw JSON", async () => {
    renderActionDetail("act_custom_segments");
    await waitFor(() =>
      expect(
        screen.getByRole("heading", {
          name: "Przygotuj propozycje segmentów z wyszukiwanych haseł"
        })
      ).toBeInTheDocument()
    );
    expect(screen.getByText("Segment odbiorców do sprawdzenia")).toBeInTheDocument();
    expect(screen.getByText("ocena segmentu bez zapisu zmian")).toBeInTheDocument();
    expect(screen.getByText(/Nazwa: Segment z wyszukiwanych haseł/)).toBeInTheDocument();
    expect(screen.getByText(/Typ odbiorców: słowa kluczowe/)).toBeInTheDocument();
    expect(screen.getByText(/Hasła źródłowe: alba czeladź/)).toBeInTheDocument();
    expect(screen.getByText(/Kampania do sprawdzenia: Kompendium PPWR/)).toBeInTheDocument();
    expect(screen.getByText(/Bezpieczeństwo: zablokowane/)).toBeInTheDocument();
    expect(screen.getByText(/Braki: prognoza albo rozmiar odbiorców/)).toBeInTheDocument();
    expect(screen.queryByText(/WILQ search-term intent review/)).not.toBeInTheDocument();
    expect(screen.queryByText(/KEYWORD/)).not.toBeInTheDocument();
    expect(screen.queryByText(/23848569273/)).not.toBeInTheDocument();
    expect(screen.getAllByText(/Zapis zmian:/).length).toBeGreaterThan(0);
  });

  it("renders negative keyword change preview without requiring raw JSON", async () => {
    renderActionDetail("act_negative_keywords");
    await waitFor(() =>
      expect(
        screen.getByRole("heading", {
          name: "Przygotuj kolejkę oceny wykluczeń z wyszukiwanych haseł"
        })
      ).toBeInTheDocument()
    );
    expect(screen.getByText("Wykluczenie słowa do sprawdzenia")).toBeInTheDocument();
    expect(screen.getByText("ocena intencji zapytania bez zapisu zmian")).toBeInTheDocument();
    expect(screen.getByText(/Hasło: alba czeladź/)).toBeInTheDocument();
    expect(screen.getByText(/Wykluczenie: alba czeladź/)).toBeInTheDocument();
    expect(screen.getByText(/Dopasowanie: dopasowanie ścisłe/)).toBeInTheDocument();
    expect(screen.getByText(/Poziom: grupa reklam/)).toBeInTheDocument();
    expect(screen.getByText(/Kampania: Kompendium PPWR/)).toBeInTheDocument();
    expect(screen.getByText(/Grupa reklam: Grupa reklam 1/)).toBeInTheDocument();
    expect(screen.queryByText(/EXACT/)).not.toBeInTheDocument();
    expect(screen.queryByText(/ad_group/)).not.toBeInTheDocument();
    expect(screen.queryByText(/23848569273/)).not.toBeInTheDocument();
    expect(screen.queryByText(/203360679544/)).not.toBeInTheDocument();
    expect(screen.getAllByText(/Zapis zmian:/).length).toBeGreaterThan(0);
  });

  it("renders search-term n-gram preview without requiring raw JSON", async () => {
    renderActionDetail("act_ngrams");
    await waitFor(() =>
      expect(
        screen.getByRole("heading", {
          name: "Przygotuj ocenę tematów z n-gramów wyszukiwanych haseł"
        })
      ).toBeInTheDocument()
    );
    expect(screen.getByText("Temat zapytań do sprawdzenia")).toBeInTheDocument();
    expect(screen.getByText(/Temat: asekol/)).toBeInTheDocument();
    expect(screen.getByText(/Rozmiar: 1/)).toBeInTheDocument();
    expect(screen.getByText(/Zapytania użytkowników: 1/)).toBeInTheDocument();
    expect(screen.getByText(/Przykłady: asekol pl organizacja odzysku/)).toBeInTheDocument();
    expect(screen.getByText(/Kliknięcia: 1/)).toBeInTheDocument();
    expect(screen.getByText(/Wyświetlenia: 1/)).toBeInTheDocument();
    expect(screen.getByText(/Koszt: 24.17 PLN/)).toBeInTheDocument();
    expect(screen.getByText(/Konwersje: 0/)).toBeInTheDocument();
    expect(screen.getByText(/Braki: ręczna ocena intencji/)).toBeInTheDocument();
    expect(screen.getByText(/Czego nie wolno twierdzić: marnowanie budżetu na zapytaniach/)).toBeInTheDocument();
    expect(screen.getAllByText(/Zapis zmian:/).length).toBeGreaterThan(0);
  });

  it("renders Demand Gen readiness preview without requiring raw JSON", async () => {
    renderActionDetail("act_demand_gen");
    await waitFor(() =>
      expect(
        screen.getByRole("heading", {
          name: "Przygotuj sprawdzenie gotowości Demand Gen"
        })
      ).toBeInTheDocument()
    );
    expect(screen.getByText("Gotowość Demand Gen do sprawdzenia")).toBeInTheDocument();
    expect(screen.getByText(/Kampanie ocenione: 20/)).toBeInTheDocument();
    expect(screen.getByText(/Kanały kampanii: PMax: 8, Search: 10, nieznany kanał: 2/)).toBeInTheDocument();
    expect(screen.getByText(/Kampanie Demand Gen: 0/)).toBeInTheDocument();
    expect(screen.getByText(/Kreacje i zasoby: 0/)).toBeInTheDocument();
    expect(screen.getByText(/Braki: jakość stron wejścia Demand Gen według kampanii/)).toBeInTheDocument();
    expect(screen.queryByText(/PERFORMANCE_MAX/)).not.toBeInTheDocument();
    expect(screen.queryByText(/UNKNOWN/)).not.toBeInTheDocument();
    expect(screen.getAllByText(/Zapis zmian:/).length).toBeGreaterThan(0);
  });

  it("renders GA4 tracking-quality preview without requiring raw JSON", async () => {
    renderActionDetail("act_ga4_tracking");
    await waitFor(() =>
      expect(
        screen.getByRole("heading", {
          name: "Sprawdź jakość pomiaru GA4 przed oceną kampanii"
        })
      ).toBeInTheDocument()
    );
    expect(screen.getByText("Jakość pomiaru GA4 do sprawdzenia")).toBeInTheDocument();
    expect(screen.getByText(/Strona wejścia: \//)).toBeInTheDocument();
    expect(screen.getByText(/Źródło: google \/ cpc/)).toBeInTheDocument();
    expect(screen.getByText(/Kampania: \(2026\) Ekologus Ogólna/)).toBeInTheDocument();
    expect(screen.getByText(/Aktywni użytkownicy: 49/)).toBeInTheDocument();
    expect(screen.getByText(/Sesje: 77/)).toBeInTheDocument();
    expect(screen.getByText(/Współczynnik zaangażowania: 76,62%/)).toBeInTheDocument();
    expect(screen.getByText(/Zdarzenia: 1190/)).toBeInTheDocument();
    expect(screen.getByText(/Warunki sprawdzenia: sprawdź stronę wejścia/)).toBeInTheDocument();
    expect(screen.getByText(/Czego nie wolno twierdzić: współczynnik konwersji/)).toBeInTheDocument();
    expect(screen.getAllByText(/Zapis zmian:/).length).toBeGreaterThan(0);
  });

  it("renders Localo visibility preview without requiring raw JSON", async () => {
    renderActionDetail("act_localo");
    await waitFor(() =>
      expect(
        screen.getByRole("heading", {
          name: "Przygotuj sprawdzenie widoczności lokalnej Localo"
        })
      ).toBeInTheDocument()
    );
    expect(screen.getByText("Widoczność lokalna do sprawdzenia")).toBeInTheDocument();
    expect(screen.getByText(/Widoczność: 53,174/)).toBeInTheDocument();
    expect(screen.getByText(/Zmiana widoczności: 69,57%/)).toBeInTheDocument();
    expect(screen.getByText(/Średnia pozycja grid: 3,263/)).toBeInTheDocument();
    expect(screen.getByText(/Monitorowane frazy: 23/)).toBeInTheDocument();
    expect(screen.getByText(/Aktywne miejsca: 4/)).toBeInTheDocument();
    expect(screen.getByText(/Ocena: 4,75/)).toBeInTheDocument();
    expect(screen.getByText(/Opinie: 798/)).toBeInTheDocument();
    expect(screen.getByText(/Odsetek odpowiedzi na opinie: 81,33%/)).toBeInTheDocument();
    expect(screen.getByText(/Dozwolone odczyty: lokalne pozycje/)).toBeInTheDocument();
    expect(screen.getByText(/Braki: widoczność Google Business Profile/)).toBeInTheDocument();
    expect(screen.getByText(/Czego nie wolno twierdzić: wyniki profilu firmy w Google/)).toBeInTheDocument();
    expect(screen.getAllByText(/Zapis zmian:/).length).toBeGreaterThan(0);
  });

  it("renders social source inputs without requiring raw JSON", async () => {
    renderActionDetail("act_social_draft");
    await waitFor(() =>
      expect(
        screen.getByRole("heading", {
          name: "Przygotuj propozycje postów LinkedIn z dowodów WILQ"
        })
      ).toBeInTheDocument()
    );
    expect(screen.getAllByText("Materiał do posta do sprawdzenia").length).toBeGreaterThan(0);
    expect(screen.getByText(/Źródło danych: Google Search Console/)).toBeInTheDocument();
    expect(screen.getByText(/Sygnał: kliknięcia/)).toBeInTheDocument();
    expect(screen.getByText(/Wartość: 12/)).toBeInTheDocument();
    expect(screen.getByText(/Kontekst: sygnał z Google Search Console/)).toBeInTheDocument();
    expect(screen.getByText(/Źródło danych: Merchant Center/)).toBeInTheDocument();
    expect(screen.getByText(/Sygnał: zgłoszenia problemów/)).toBeInTheDocument();
    expect(screen.getByText(/Wartość: 14/)).toBeInTheDocument();
    expect(screen.getByText(/Kontekst: zgłoszenie problemu danych produktowych Merchant Center/)).toBeInTheDocument();
    expect(screen.queryByText(/Szczegóły źródłowe/)).not.toBeInTheDocument();
    expect(screen.queryByText(/google_search_console/)).not.toBeInTheDocument();
    expect(screen.queryByText(/google_merchant_center/)).not.toBeInTheDocument();
    expect(screen.queryByText(/issue_product_count/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Metryka: clicks/)).not.toBeInTheDocument();
    expect(screen.getAllByText(/Ograniczenia: użyj tylko dowodów z WILQ/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Czego nie wolno twierdzić: zwrot z reklam/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/zapis zmian zablokowany/).length).toBeGreaterThan(0);
  });

  it("renders Keyword Planner access blocker without requiring raw JSON", async () => {
    renderActionDetail("act_keyword_planner_access");
    await waitFor(() =>
      expect(
        screen.getByRole("heading", {
          name: "Odblokuj Keyword Planner dla Google Ads"
        })
      ).toBeInTheDocument()
    );
    expect(screen.getByText("Dostęp do Keyword Plannera do odblokowania")).toBeInTheDocument();
    expect(screen.getByText("blokada dostępu bez zapisu zmian")).toBeInTheDocument();
    expect(screen.getByText(/Zablokowany dostęp: Keyword Planner/)).toBeInTheDocument();
    expect(
      screen.getByText(
        /Powód: token deweloperski nie ma zatwierdzonego dostępu do Keyword Plannera/
      )
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Wymagany stan: token deweloperski zatwierdzony dla Keyword Plannera/)
    ).toBeInTheDocument();
    expect(screen.queryByText(/api_code=403/)).not.toBeInTheDocument();
    expect(screen.queryByText(/DEVELOPER_TOKEN_NOT_APPROVED/)).not.toBeInTheDocument();
    expect(screen.getAllByText(/Zapis zmian:/).length).toBeGreaterThan(0);
  });

  it("renders Ads target guardrail preview without requiring raw JSON", async () => {
    renderActionDetail("act_ads_target_guardrails");
    await waitFor(() =>
      expect(
        screen.getByRole("heading", {
          name: "Potwierdź docelowy zwrot z reklam albo koszt pozyskania celu dla Ads"
        })
      ).toBeInTheDocument()
    );
    expect(screen.getByText("Zasady bezpieczeństwa Ads do sprawdzenia")).toBeInTheDocument();
    expect(screen.getByText(/Marża: 30%/)).toBeInTheDocument();
    expect(screen.getByText(/Cel biznesowy: wstępny review jakości leadów/)).toBeInTheDocument();
    expect(screen.getByText(/Cel budżetu: wstępnie chronić obecny budżet/)).toBeInTheDocument();
    expect(screen.getByText(/Docelowy zwrot z reklam: brak/)).toBeInTheDocument();
    expect(screen.getByText(/Docelowy koszt pozyskania celu: brak/)).toBeInTheDocument();
    expect(screen.getByText(/Braki: docelowy zwrot z reklam albo koszt pozyskania celu/)).toBeInTheDocument();
    expect(screen.getByText(/Opcje celu: docelowy zwrot z reklam, docelowy koszt pozyskania celu/)).toBeInTheDocument();
    expect(screen.getByText(/Po potwierdzeniu: przegląd wskaźników względem celu/)).toBeInTheDocument();
    expect(screen.getByText(/Warunki sprawdzenia: sprawdź model marży/)).toBeInTheDocument();
    expect(screen.getByText(/Czego nie wolno twierdzić: ocena KPI względem celu przed potwierdzeniem/)).toBeInTheDocument();
    expect(screen.getAllByText(/Zapis zmian:/).length).toBeGreaterThan(0);
  });

  it("renders Ads strategy review guardrail preview without requiring raw JSON", async () => {
    renderActionDetail("act_ads_strategy_review");
    await waitFor(() =>
      expect(
        screen.getByRole("heading", {
          name: "Zapisz ocenę strategii Ads przez człowieka"
        })
      ).toBeInTheDocument()
    );
    expect(screen.getByText("Zasady bezpieczeństwa Ads do sprawdzenia")).toBeInTheDocument();
    expect(screen.getByText(/Marża: 30%/)).toBeInTheDocument();
    expect(screen.getByText(/Ostatni przegląd strategii: brak/)).toBeInTheDocument();
    expect(screen.getByText(/Warunki przeglądu: człowiek sprawdza strategię/)).toBeInTheDocument();
    expect(screen.getByText(/Warunki sprawdzenia: sprawdź model marży/)).toBeInTheDocument();
    expect(screen.getByText(/Czego nie wolno twierdzić: ocena opłacalności/)).toBeInTheDocument();
    expect(screen.getAllByText(/Zapis zmian:/).length).toBeGreaterThan(0);
  });

  it("renders content plan and WordPress podgląd szkicu without requiring raw JSON", async () => {
    renderActionDetail("act_content");
    await waitFor(() =>
      expect(
        screen.getByRole("heading", {
          name: "Przygotuj kolejkę odświeżenia treści ekologus.pl"
        })
      ).toBeInTheDocument()
    );
    expect(screen.getAllByText("Plan treści do sprawdzenia").length).toBeGreaterThan(0);
    expect(screen.queryByText("Brief treści do sprawdzenia")).not.toBeInTheDocument();
    expect(screen.getAllByText(/Temat: bdo co to/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Tryb: sprawdzić spis treści/).length).toBeGreaterThan(0);
    expect(screen.queryByText(/wymaga etykiety trybu z WILQ/)).not.toBeInTheDocument();
    expect(screen.getAllByText(/Opcje: odśwież istniejącą treść, scal z istniejącą treścią/).length).toBeGreaterThan(0);
    expect(screen.getByText(/Kąt treści: Najpierw potwierdź kanoniczną stronę BDO/)).toBeInTheDocument();
    expect(screen.getByText(/H1: H1 ma jasno odpowiedzieć na intencję `bdo co to`/)).toBeInTheDocument();
    expect(screen.getByText(/Brakujące dowody: brak potwierdzonego kanonicznego URL/)).toBeInTheDocument();
    expect(screen.getAllByText(/Warunki sprawdzenia: istniejący URL potwierdzony w WordPress/).length).toBeGreaterThan(0);
    expect(screen.getByText("Szkic WordPress do sprawdzenia")).toBeInTheDocument();
    expect(screen.queryByText(/Kandydat: content_brief_gsc_bdo/)).not.toBeInTheDocument();
    expect(screen.getByText(/Tytuł szkicu: Odświeżenie: zielony ład/)).toBeInTheDocument();
    expect(screen.getByText(/Kontrole treści: spis treści: spis potwierdzony/)).toBeInTheDocument();
    expect(screen.getByText(/Szkic WordPress: status: zablokowany/)).toBeInTheDocument();
    expect(screen.getAllByText(/Zapis zmian:/).length).toBeGreaterThan(0);
  });

  it("keeps action detail labels sourced from API payload labels", () => {
    const source = readFileSync("src/routes/DetailPanels.tsx", "utf8");

    expect(source).not.toContain("from \"./marketingLabels\"");
    expect(source).not.toContain("adsMissingReadContractLabel");
    expect(source).not.toContain("marketerBlockedClaimLabels");
    expect(source).not.toContain("contentWordPressPostStatusLabel");
    expect(source).not.toContain("contentBrief");
    expect(source).not.toContain("wordpressDraft");
    expect(source).not.toContain("wordpressDraftHandoff");
    expect(source).not.toContain("searchTermNgram");
    expect(source).toContain("action.preview_cards");
    expect(source).toContain("allowed_contract_labels");
    expect(source).toContain("target_roas_or_cpa_labels");
  });
});
