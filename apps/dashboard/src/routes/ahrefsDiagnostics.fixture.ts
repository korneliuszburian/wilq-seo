export const ahrefsDiagnostics = {
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
    summary: "WILQ ma 2 rekordy luk z Ahrefs. Brakujące dane: Dane kompletne dla tej decyzji.",
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
      "organiczne słowa dla URL",
      "najlepsze strony konkurencji"
    ],
    missing_read_contracts: [],
    missing_read_contract_labels: [],
    missing_read_contract_summary_label: "Dane kompletne dla tej decyzji",
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
    blocked_claim_summary_label: "2 zablokowane obietnice",
    operator_review_gates: [
      "ahrefs_gap_records_required",
      "content_workflow_review_required",
      "human_strategy_review"
    ],
    operator_review_gate_labels: [
      "wymagane konkretne rekordy luk Ahrefs",
      "sprawdzenie w workflow treści",
      "sprawdzenie strategii przez człowieka"
    ],
    source_connectors: ["ahrefs"],
    evidence_ids: ["ev_refresh_refresh_ahrefs_test"],
    evidence_summary_label: "1 dowód źródłowy",
    action_ids: [],
    action_summary_label: "Nie ma akcji do sprawdzenia; zostaje ręczna ocena",
    gap_records: [
      {
        id: "ahrefs_gap_content_gap_test",
        gap_type: "content_gap",
        gap_type_label: "luka treści",
        title: "Luka treści: audyt środowiskowy",
        summary:
          "Luka treści: audyt środowiskowy. Dane Ahrefs: content_gaps=1. To jest materiał do sprawdzenia, nie obietnica wzrostu ruchu.",
        source_url: "https://competitor.example/audyt-srodowiskowy",
        referenced_public_url: null,
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
        title: "Luka linków zwrotnych: example.org",
        summary:
          "Luka linków zwrotnych: example.org. Dane Ahrefs: referring_domain_gaps=1. To jest materiał do sprawdzenia, nie obietnica wzrostu ruchu.",
        source_url: "example.org",
        referenced_public_url: null,
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
        referenced_public_url: null,
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
        referenced_public_url: null,
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
        referenced_public_url: null,
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
        referenced_public_url: null,
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
    cross_check_status: "api_backed",
    cross_check_status_label: "sprawdzenie GSC/WordPress ma dopasowania z API",
    cross_check_summary:
      "WILQ znalazł 1 kandydata Ahrefs do walidacji: 1 ma dopasowanie w GSC, a 1 ma dopasowanie w spisie WordPress.",
    cross_check_next_step:
      "Otwórz kandydatów z dopasowaniem GSC/WordPress i zdecyduj: brief, scalenie, obserwacja albo blokada tematu.",
    cross_check_gsc_match_count: 1,
    cross_check_wordpress_match_count: 1,
    cross_check_source_connectors: ["google_search_console", "wordpress_ekologus"],
    cross_check_evidence_ids: ["ev_refresh_gsc_cross_check", "ev_refresh_wp_cross_check"],
    cross_check_candidates: [
      {
        id: "ahrefs_candidate_audyt_srodowiskowy",
        topic: "audyt środowiskowy",
        gap_type: "content_gap",
        gap_type_label: "luka treści",
        relevance_status: "relevant",
        relevance_status_label: "pasuje",
        relevance_score: 6,
        business_relevance_reasons: ["gsc_overlap", "wordpress_inventory_overlap"],
        business_relevance_reason_labels: ["pokrywa się z GSC", "pokrywa się z WordPress"],
        gsc_demand: "present",
        gsc_demand_label: "jest w GSC",
        gsc_cross_check: {
          strength: "exact",
          label: "potwierdzone dopasowanie w GSC",
          matching_labels: ["audyt środowiskowy"],
          source_connectors: ["google_search_console"],
          evidence_ids: ["ev_refresh_gsc_cross_check"]
        },
        wordpress_inventory_match: "present",
        wordpress_inventory_match_label: "jest w WordPress",
        wordpress_cross_check: {
          strength: "exact",
          label: "potwierdzone dopasowanie w WordPress",
          matching_labels: ["https://www.ekologus.pl/audyt-srodowiskowy/"],
          source_connectors: ["wordpress_ekologus"],
          evidence_ids: ["ev_refresh_wp_cross_check"]
        },
        gsc_overlap_terms: ["audyt środowiskowy"],
        wordpress_overlap_urls: ["https://www.ekologus.pl/audyt-srodowiskowy/"],
        keyword: "audyt środowiskowy",
        competitor_domain: "competitor.example",
        source_url: "https://competitor.example/audyt-srodowiskowy",
        referenced_public_url: null,
        metric_name: "ahrefs_content_gap_count",
        metric_value: 1,
        source_connectors: ["ahrefs", "google_search_console", "wordpress_ekologus"],
        evidence_ids: ["ev_refresh_refresh_ahrefs_test"],
        next_step:
          "Zweryfikuj audyt środowiskowy z GSC i spisem treści WordPress, potem zdecyduj: odświeżenie, scalenie, utworzenie albo blokada."
      }
    ],
    next_step: "Połącz luki Ahrefs z GSC i WordPress i przygotuj kolejkę sprawdzenia.",
    risk: "medium"
  },
  operator_summary: {
    id: "ahrefs_operator_summary",
    title: "Co marketer ma wiedzieć o Ahrefs",
    summary:
      "Ten widok pokazuje, czy Ahrefs może wesprzeć decyzje SEO i treści. Autorytet domeny może być kontekstem, ale wnioski o lukach treści lub lukach linków zwrotnych wymagają konkretnych danych Ahrefs.",
    next_step:
      "Użyj najważniejszych decyzji Ahrefs jako kontekstu dla widoku Treści. Nie twierdź o lukach treści, lukach linków ani wzroście widoczności bez konkretnych danych Ahrefs.",
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
      "organiczne słowa dla URL",
      "najlepsze strony konkurencji"
    ],
    missing_read_contracts: [],
    missing_read_contract_labels: [],
    source_connectors: ["ahrefs"],
    evidence_ids: ["ev_refresh_refresh_ahrefs_test"],
    evidence_summary_label: "1 dowód źródłowy",
    action_ids: [],
    action_summary_label: "Nie ma akcji do sprawdzenia; zostaje ręczna ocena",
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
        "WILQ ma metryki autorytetu Ahrefs z dowodami, więc może dodać kontekst autorytetu do sprawdzenia SEO i treści. To nadal nie jest analiza luk.",
      next_step:
        "Połącz ten kontekst z widokiem Treści i GSC. Nie twierdź, że Ahrefs wykrył lukę treści/linków.",
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
      evidence_summary_label: "1 dowód źródłowy",
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
      action_summary_label: "Nie ma akcji do sprawdzenia; zostaje ręczna ocena",
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
        "WILQ ma 2 rekordy luk z Ahrefs. Brakujące dane: Dane kompletne dla tej decyzji.",
      rationale:
        "To są konkretne rekordy z dowodami Ahrefs, więc mogą wejść do sprawdzenia SEO i treści.",
      next_step:
        "Połącz rekordy z widokiem Treści, sprawdź duplikaty WordPress i przygotuj zachowanie, odświeżenie, scalenie, utworzenie albo blokadę zamiast obiecywać wzrost.",
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
      evidence_summary_label: "1 dowód źródłowy",
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
      action_summary_label: "Nie ma akcji do sprawdzenia; zostaje ręczna ocena",
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
      evidence_summary_label: "1 dowód źródłowy",
      metric_facts: [],
      metric_fact_labels: {},
      action_ids: [],
      action_summary_label: "Nie ma akcji do sprawdzenia; zostaje ręczna ocena",
      blocked_claims: [],
      blocked_claim_labels: [],
      risk: "low"
    },
    {
      id: "ahrefs_gap_contract",
      title: "Ahrefs: rekordy luk SEO",
      status: "ready",
      status_label: "gotowe",
      summary: "WILQ ma konkretne luki treści i linków zwrotnych z Ahrefs.",
      diagnosis: "To jest materiał do sprawdzenia, nie automatyczna obietnica wzrostu.",
      next_step: "Połącz rekordy z GSC i Spis treści WordPress przed decyzją contentową.",
      source_connectors: ["ahrefs"],
      evidence_ids: ["ev_refresh_refresh_ahrefs_test"],
      evidence_summary_label: "1 dowód źródłowy",
      metric_facts: [],
      metric_fact_labels: {},
      action_ids: [],
      action_summary_label: "Nie ma akcji do sprawdzenia; zostaje ręczna ocena",
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
  evidence_summary_label: "3 dowody źródłowe",
  source_connector_labels: ["Ahrefs"],
  action_ids: [],
  action_summary_label: "Nie ma akcji do sprawdzenia; zostaje ręczna ocena",
  blocker_count: 1
};
