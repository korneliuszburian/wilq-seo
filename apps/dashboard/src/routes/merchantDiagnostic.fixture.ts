const merchantMetricFacts = [
  {
    name: "total_products",
    metric_label: "produkty w pliku produktowym",
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
    metric_label: "zgłoszenia problemów",
    value: 23,
    period: "connector_refresh",
    source_connector: "google_merchant_center",
    evidence_id: "ev_refresh_merchant_feed",
    dimensions: { issue_type: "availability_updated" },
    unit: null,
    collected_at: "2026-06-17T10:00:00Z",
    previous_value: 23,
    delta: 0,
    delta_percent: 0,
    trend: "flat",
    freshness_state: "fresh",
    freshness_label: "odświeżone mniej niż godzinę temu"
  }
];

const merchantTacticalItem = {
  id: "tq_merchant_issue",
  title: "Merchant: problem z dostępnością; zmiana dostępności; kraj PL",
  domain: "merchant",
  intent: "merchant_feed_triage",
  priority: 27,
  risk: "medium",
  source_connectors: ["google_merchant_center"],
  evidence_ids: ["ev_refresh_merchant_feed"],
  metric_facts: [merchantMetricFacts[1]],
  dimensions: { issue_type: "availability_updated", affected_attribute: "n:availability" },
  diagnosis: "Merchant issue availability_updated dotyczy atrybutu n:availability.",
  next_step: "Przygotuj kolejkę przeglądu bez zmiany głównego pliku produktowego.",
  blocked_claims: ["automatyczna zmiana pliku produktowego", "ponowne zatwierdzenie produktu"],
  action_ids: ["act_review_merchant_feed_issues"]
};

export const merchantDiagnostics = {
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
    capabilities: {
      read: true,
      write: false,
      read_adapter: "merchant_api",
      mutation_adapter: null,
      action_scope: "review_only",
      blockers: ["vendor_write_not_implemented"],
      operations: ["merchant_feed_issue"]
    },
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
  live_data_status_label: "metryki pliku produktowego dostępne",
  product_count: 10900,
  issue_count: 23,
  freshness_assessment: {
    state: "stale",
    state_label: "dane do odświeżenia",
    checked_at: "2026-06-17T10:00:02Z",
    latest_refresh_id: "refresh_google_merchant_center_test",
    latest_refresh_completed_at: "2026-06-17T10:00:01Z",
    age_hours: 73,
    stale_after_hours: 48,
    requires_refresh: true,
    summary: "Ostatni odczyt danych Merchant ma około 73h.",
    next_step: "Uruchom odczyt danych Merchant, jeśli pytanie dotyczy aktualnego stanu produktów."
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
      blocked_claims: ["naprawa pojedynczego produktu", "zapis do pliku produktowego", "automatyczna zmiana pliku produktowego"],
      blocked_claim_labels: ["naprawa pojedynczego produktu", "zapis do pliku produktowego", "automatyczna zmiana pliku produktowego"]
    },
    {
      id: "merchant_product_performance_join_missing",
      title: "Brak połączenia produktów Merchant z Ads/GA4",
      reason:
        "Merchant diagnostics ma przykładowe produkty, ale brakuje dopasowanych faktów Ads/GA4 po product_id albo item_id.",
      impact:
        "WILQ może prowadzić review pliku produktowego, ale nie może wskazać werdyktu zwrotu z reklam na poziomie produktu ani twierdzenia o wpływie naprawy na przychód.",
      next_step:
        "Dodać skuteczność produktu dla Google Ads Shopping, Performance Max i GA4 ecommerce.",
      blocked_claims: ["werdykt zwrotu z reklam na poziomie produktu", "twierdzenie o odzyskanym przychodzie produktu", "efekt naprawy produktu"],
      blocked_claim_labels: ["werdykt zwrotu z reklam na poziomie produktu", "twierdzenie o odzyskanym przychodzie produktu", "efekt naprawy produktu"]
    }
  ],
  product_sample_readiness: {
    status: "ready",
    status_label: "próbki produktów dostępne",
    sample_products_available: true,
    sample_count: 2,
    sample_product_ids: ["online~pl~PL~SKU-001", "online~pl~PL~SKU-002"],
    sample_product_titles: ["Sorbent chemiczny 10 kg"],
    sample_summary_label: "2 próbki produktów do sprawdzenia",
    sample_title_labels: ["Sorbent chemiczny 10 kg"],
    current_read_contract: "merchant_aggregate_product_statuses",
    required_read_contracts: [
      "merchant_products_list_product_status",
      "merchant_reports_product_view_issue_filter"
    ],
    source_endpoint: "aggregateProductStatuses",
    summary:
      "Merchant diagnostics ma przykładowe produkty do review, ale nie jest pełną listą SKU do edycji.",
    next_step:
      "Użyj próbek jako punktu startu przeglądu i nie zapisuj zmian pliku produktowego bez podglądu zmian.",
    blocked_claims: ["naprawa pojedynczego produktu", "zapis do pliku produktowego", "automatyczna zmiana pliku produktowego"],
    blocked_claim_labels: ["naprawa pojedynczego produktu", "zapis do pliku produktowego", "automatyczna zmiana pliku produktowego"]
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
    sample_product_summary_label: "2 próbki produktów do sprawdzenia",
    performance_rows: [],
    source_connectors: ["google_merchant_center"],
    source_connector_labels: ["Merchant Center"],
    evidence_ids: ["ev_refresh_merchant_feed"],
    evidence_summary_label: "1 dowód źródłowy",
    summary:
      "Merchant ma próbki produktów, ale WILQ nie ma jeszcze dopasowanych faktów produktu z Ads/GA4.",
    next_step:
      "Dodać skuteczność produktu dla Google Ads Shopping, Performance Max i GA4 ecommerce ze wspólnym kluczem produktu.",
    blocked_claims: [
      "werdykt zwrotu z reklam na poziomie produktu",
      "twierdzenie o odzyskanym przychodzie produktu",
      "efekt naprawy produktu",
      "skalowanie produktu w reklamach produktowych i Performance Max",
      "ponowne zatwierdzenie produktu",
      "zapis do pliku produktowego"
    ],
    blocked_claim_labels: [
      "werdykt zwrotu z reklam na poziomie produktu",
      "twierdzenie o odzyskanym przychodzie produktu",
      "efekt naprawy produktu",
      "skalowanie produktu w reklamach produktowych i Performance Max",
      "ponowne zatwierdzenie produktu",
      "zapis do pliku produktowego"
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
    preview_cards: [
      {
        id: "merchant_price_impact_readiness_preview",
        kind: "merchant_review_preview",
        title_label: "Podgląd sprawdzenia Merchant",
        subtitle_label: "sprawdzenie wpływu ceny",
        status_label: "do sprawdzenia",
        rows: [
          { label: "Typ sprawdzenia", value: "sprawdzenie wpływu ceny" },
          { label: "Zakres", value: "zakres do ustalenia w review" },
          { label: "Warunki sprawdzenia", value: "potwierdź historię ceny" }
        ],
        apply_state_label: "Zapis zmian jest zablokowany.",
        system_readiness_label: "System nie ma gotowego kontraktu zapisu dla tej akcji."
      }
    ],
    source_connectors: ["google_merchant_center"],
    source_connector_labels: ["Merchant Center"],
    evidence_ids: ["ev_refresh_merchant_feed"],
    evidence_summary_label: "1 dowód źródłowy",
    summary:
      "Brak historii ceny i okna performance, więc WILQ nie ocenia wpływu zmian cen na produkt.",
    next_step:
      "Dodać historię ceny i okno skuteczności produktu przed oceną wpływu zmiany ceny.",
    blocked_claims: ["wpływ zmiany ceny", "werdykt zwrotu z reklam na poziomie produktu", "twierdzenie o odzyskanym przychodzie produktu"],
    blocked_claim_labels: ["wpływ zmiany ceny", "werdykt zwrotu z reklam na poziomie produktu", "twierdzenie o odzyskanym przychodzie produktu"]
  },
  operator_summary: {
    id: "merchant_operator_summary",
    title: "Co marketer ma zrobić teraz z plikiem produktowym",
    summary:
      "WILQ grupuje problemy Merchant po typie i atrybucie. To jest kolejka przeglądu: można przygotować decyzje i podgląd zmian, ale nie wolno obiecać ponownego zatwierdzenia produktu ani automatycznie nadpisać pliku produktowego.",
    next_step:
      "Przejdź przez top decyzje lub klastry problemów, przygotuj akcję do sprawdzenia i nie zapisuj zmian pliku produktowego bez sprawdzenia w WILQ oraz zgody operatora.",
    top_decision_ids: [
      "merchant_decision_merchant_issue_pl_not_impacted_availability_updated_n_availability"
    ],
    top_issue_cluster_ids: ["merchant_issue_pl_not_impacted_availability_updated_n_availability"],
    top_tactical_item_ids: ["tq_merchant_issue"],
    reported_issue_occurrences: 23,
    decision_source: "decision_queue",
    decision_source_label: "kolejka decyzji Merchant",
    drilldown_source: "issue_clusters",
    drilldown_source_label: "grupy problemów pliku produktowego",
    count_semantics: "reported_issue_occurrences",
    count_semantics_label: "wystąpienia problemów w raportach",
    issue_types: ["zmiana dostępności"],
    source_connectors: ["google_merchant_center"],
    source_connector_labels: ["Merchant Center"],
    evidence_ids: ["ev_refresh_merchant_feed"],
    evidence_summary_label: "1 dowód źródłowy",
    action_ids: ["act_review_merchant_feed_issues"],
    action_summary_label: "1 akcja do sprawdzenia",
    blocked_claims: [
      "ponowne zatwierdzenie produktu",
      "twierdzenie o odzyskanym przychodzie",
      "automatyczna zmiana pliku produktowego",
      "nadpisanie głównego pliku produktowego"
    ],
    blocked_claim_labels: [
      "ponowne zatwierdzenie produktu",
      "twierdzenie o odzyskanym przychodzie",
      "automatyczna zmiana pliku produktowego",
      "nadpisanie głównego pliku produktowego"
    ]
  },
  issue_clusters: [
    {
      id: "merchant_issue_pl_not_impacted_availability_updated_n_availability",
      issue_type: "availability_updated",
      issue_type_label: "zmiana dostępności",
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
      reported_issue_summary_label: "23 zgłoszenia problemu",
      count_semantics: "reported_issue_occurrences",
      sample_product_ids: ["online~pl~PL~SKU-001", "online~pl~PL~SKU-002"],
      sample_titles: ["Sorbent chemiczny 10 kg"],
      sample_unavailable_reason: null,
      source_connectors: ["google_merchant_center"],
      evidence_ids: ["ev_refresh_merchant_feed"],
      blocked_claims: ["ponowne zatwierdzenie produktu", "twierdzenie o odzyskanym przychodzie", "automatyczna zmiana pliku produktowego"],
      action_id: "act_review_merchant_feed_issues",
      risk: "medium",
      next_step:
        "Przejrzyj tę grupę problemu przez akcję do sprawdzenia; najpierw przygotuj podgląd zmian, bez automatycznej zmiany pliku produktowego."
    }
  ],
  decision_queue: [
    {
      id: "merchant_decision_merchant_issue_pl_not_impacted_availability_updated_n_availability",
      decision_type: "review_issue_cluster",
      decision_type_label: "przegląd problemu pliku produktowego",
      status: "ready",
      status_label: "gotowe",
      title: "Merchant: problem z atrybutem: dostępność - zmiana dostępności",
      summary:
        "23 zgłoszenia problemu. Status: bez wpływu. Zalecenie: wymaga działania po stronie Merchant. Zakres: dla kraju PL; kontekst: reklamy produktowe.",
      cluster_id: "merchant_issue_pl_not_impacted_availability_updated_n_availability",
      issue_cluster_ids: ["merchant_issue_pl_not_impacted_availability_updated_n_availability"],
      issue_type: "availability_updated",
      issue_type_label: "zmiana dostępności",
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
      preview_cards: [
        {
          id: "merchant_feed_issue_review_merchant_issue_pl_not_impacted_availability_updated_n_availability",
          kind: "merchant_review_preview",
          title_label: "Podgląd sprawdzenia Merchant",
          subtitle_label: "sprawdzenie problemów pliku produktowego",
          status_label: "do sprawdzenia",
          rows: [
            { label: "Typ sprawdzenia", value: "sprawdzenie problemów pliku produktowego" },
            { label: "Zakres", value: "23 zgłoszenia" },
            {
              label: "Warunki sprawdzenia",
              value: "sprawdź typ problemu i atrybut, sprawdź kontekst raportowania"
            }
          ],
          apply_state_label: "Zapis zmian jest zablokowany.",
          system_readiness_label: "System nie ma gotowego kontraktu zapisu dla tej akcji."
        }
      ],
      source_connectors: ["google_merchant_center"],
      source_connector_labels: ["Merchant Center"],
      evidence_ids: ["ev_refresh_merchant_feed"],
      evidence_summary_label: "1 dowód źródłowy",
      metric_facts: [merchantMetricFacts[1]],
      action_ids: ["act_review_merchant_feed_issues"],
      action_summary_label: "1 akcja do sprawdzenia",
      blocked_claims: ["ponowne zatwierdzenie produktu", "twierdzenie o odzyskanym przychodzie", "automatyczna zmiana pliku produktowego"],
      blocked_claim_labels: ["ponowne zatwierdzenie produktu", "twierdzenie o odzyskanym przychodzie", "automatyczna zmiana pliku produktowego"],
      rationale:
        "To jest klaster problemu Merchant do ręcznego review. Liczba oznacza wystąpienia problemu w raportach, nie gotową zmianę pliku produktowego. Przykładowe produkty służą tylko do ręcznego sprawdzenia problemu.",
      next_step:
        "Przejrzyj tę grupę problemu przez akcję do sprawdzenia; najpierw przygotuj podgląd zmian, bez automatycznej zmiany pliku produktowego.",
      risk: "medium",
      risk_label: "średnie ryzyko"
    }
  ],
  sections: [
    {
      id: "merchant_feed_health",
      label: "Metryki produktów",
      title: "Merchant Center: stan produktów i pliku produktowego",
      status: "ready",
      status_label: "gotowe",
      summary:
        "Najważniejsze metryki Merchant: produkty w pliku produktowym: 10900, zgłoszenia problemów: 23.",
      diagnosis: "WILQ ma metryki Merchant z odczytu i może ocenić skalę pliku produktowego.",
      next_step: "Przejdź do kolejki problemów i grupuj je po typie.",
      source_connectors: ["google_merchant_center"],
      evidence_ids: ["ev_refresh_merchant_feed"],
      evidence_summary_label: "1 dowód źródłowy",
      metric_facts: merchantMetricFacts,
      tactical_items: [],
      action_ids: ["act_review_merchant_feed_issues"],
      action_summary_label: "1 akcja do sprawdzenia",
      blocked_claims: ["ponowne zatwierdzenie produktu", "twierdzenie o odzyskanym przychodzie"],
      blocked_claim_labels: ["ponowne zatwierdzenie produktu", "twierdzenie o odzyskanym przychodzie"],
      risk: "medium",
      risk_label: "średnie ryzyko"
    },
    {
      id: "merchant_issue_queue",
      label: "Kolejka problemów pliku produktowego",
      title: "Merchant Center: kolejka problemów pliku produktowego",
      status: "ready",
      status_label: "gotowe",
      summary:
        "WILQ ma 1 grupę problemów pliku produktowego, 1 taktykę Merchant i 1 metrykę problemu. Liczby w grupach są wystąpieniami problemu w raportach, nie gwarancją unikalnych produktów.",
      diagnosis: "Najbezpieczniejsza praca to przegląd problemów po typie.",
      next_step: "Otwórz akcję do sprawdzenia.",
      source_connectors: ["google_merchant_center"],
      evidence_ids: ["ev_refresh_merchant_feed"],
      evidence_summary_label: "1 dowód źródłowy",
      metric_facts: [merchantMetricFacts[1]],
      tactical_items: [merchantTacticalItem],
      action_ids: ["act_review_merchant_feed_issues"],
      action_summary_label: "1 akcja do sprawdzenia",
      blocked_claims: ["automatyczna zmiana pliku produktowego", "nadpisanie głównego pliku produktowego"],
      blocked_claim_labels: ["automatyczna zmiana pliku produktowego", "nadpisanie głównego pliku produktowego"],
      risk: "medium",
      risk_label: "średnie ryzyko"
    }
  ],
  evidence_ids: [
    "ev_refresh_merchant_feed",
    "ev_refresh_merchant_issue_clusters",
    "ev_refresh_merchant_safety"
  ],
  evidence_summary_label: "3 dowody źródłowe",
  source_connector_labels: ["Merchant Center"],
  action_ids: ["act_review_merchant_feed_issues"],
  action_summary_label: "1 akcja do sprawdzenia",
  blocker_count: 0
};
