export const demandGenDiagnostics = {
  status: "blocked",
  title: "Demand Gen: brak kampanii do rekomendacji",
  summary:
    "WILQ ocenił 18 kampanii Ads. Kanały w odczycie: PMax: 8, Search: 10. Kampanie Demand Gen/Discovery: 0. WILQ ma dowody Ads i GA4 do oceny ruchu. Odczyty reklam, kreacji i jakości stron wejścia Demand Gen są dostępne, ale nadal brakuje kontroli trybu kampanii. To blokuje użyteczną rekomendację; nie jest to problem treści polecenia.",
  metric_tiles: {
    "kampanie Ads": 18,
    kanały: 2,
    "kampanie Demand Gen": 0,
    "reklamy Demand Gen": 1,
    "kreacje Demand Gen": 1,
    "strony wejścia Demand Gen": 1,
    braki: 1
  },
  available_read_contracts: [
    "google_ads_campaign_activity",
    "google_ads_budget_context",
    "google_ads_impression_share_context",
    "ga4_landing_source_campaign_quality",
    "demand_gen_readiness_review_action_object",
    "demand_gen_campaign_rows",
    "demand_gen_ad_group_ad_rows",
    "demand_gen_creative_asset_rows",
    "demand_gen_landing_quality_by_campaign"
  ],
  missing_read_contracts: ["demand_gen_campaign_mode_review"],
  available_read_contract_labels: [
    "aktywność kampanii Google Ads",
    "kontekst budżetu Google Ads",
    "udział w wyświetleniach Google Ads",
    "jakość ruchu GA4 dla stron wejścia",
    "akcja sprawdzenia Demand Gen",
    "odczyt kampanii Demand Gen/Discovery",
    "odczyt reklam Demand Gen",
    "odczyt materiałów kreatywnych",
    "jakość stron wejścia według kampanii"
  ],
  missing_read_contract_labels: ["kontrola trybu kampanii"],
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
    "gotowość trybu Demand Gen",
    "ocena jakości kreacji",
    "ocena skuteczności materiałów kreatywnych",
    "zmiana kampanii",
    "wzrost skuteczności"
  ],
  source_connectors: ["google_ads", "google_analytics_4"],
  source_connector_labels: ["Google Ads", "GA4"],
  evidence_ids: ["ev_refresh_refresh_google_ads_test", "ev_refresh_refresh_ga4_test"],
  evidence_summary_label: "2 dowody źródłowe",
  action_ids: ["act_review_demand_gen_readiness"],
  action_summary_label: "1 akcja do sprawdzenia",
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
        "demand_gen_creative_asset_rows",
        "demand_gen_landing_quality_by_campaign"
      ],
      missing_read_contracts: ["demand_gen_campaign_mode_review"],
      available_read_contract_labels: [
        "aktywność kampanii Google Ads",
        "kontekst budżetu Google Ads",
        "udział w wyświetleniach Google Ads",
        "jakość ruchu GA4 dla stron wejścia",
        "akcja sprawdzenia Demand Gen",
        "odczyt kampanii Demand Gen/Discovery",
        "odczyt reklam Demand Gen",
        "odczyt materiałów kreatywnych",
        "jakość stron wejścia według kampanii"
      ],
      missing_read_contract_labels: ["kontrola trybu kampanii"],
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
        "gotowość trybu Demand Gen",
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
  preview_cards: [
    {
      id: "demand_gen_readiness_preview_0",
      kind: "google_ads_demand_gen_readiness_review",
      title_label: "Gotowość Demand Gen do sprawdzenia",
      subtitle_label: "ocena gotowości bez zapisu zmian",
      status_label: "zapis zmian zablokowany",
      rows: [
        { label: "Kampanie ocenione", value: "18" },
        { label: "Kanały kampanii", value: "PMax: 8, Search: 10" },
        { label: "Kampanie Demand Gen", value: "0" },
        { label: "Grupy reklam Demand Gen", value: "1" },
        { label: "Kreacje i zasoby", value: "1" },
        { label: "Odczyty jakości stron wejścia", value: "1" },
        { label: "Braki", value: "kontrola trybu kampanii" },
        {
          label: "Warunki sprawdzenia",
          value:
            "sprawdzenie kanałów kampanii Ads, sprawdzenie GA4: strona wejścia, źródło ruchu i kampania"
        }
      ],
      apply_state_label: "zapis zmian zablokowany",
      system_readiness_label: "system zablokowany przed zapisem"
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
  demand_gen_landing_quality_rows: [
    {
      campaign_id: "103",
      campaign_name: "Demand Gen Test",
      landing_page: "/oferta/",
      landing_page_label: "/oferta/",
      source_medium: "google / cpc",
      source_medium_label: "google / cpc",
      active_users: 20,
      active_users_label: "20",
      sessions: 30,
      sessions_label: "30",
      engagement_rate: 0.125,
      engagement_rate_label: "12,5%",
      evidence_ids: ["ev_refresh_refresh_ga4_test"],
      evidence_summary_label: "1 dowód źródłowy"
    }
  ],
  demand_gen_campaign_mode_review_rows: [],
  next_step:
    "Sprawdź gotowość Demand Gen w WILQ jako akcję tylko do przeglądu. Zanim WILQ pokaże propozycje uruchomienia albo zmiany trybu kampanii, potwierdź kontrolę trybu kampanii.",
  risk: "medium"
};
