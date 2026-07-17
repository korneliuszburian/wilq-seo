export const localoDiagnostics = {
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
    capabilities: {
      read: true,
      write: false,
      read_adapter: "localo_mcp_oauth",
      mutation_adapter: null,
      action_scope: "review_only",
      blockers: ["vendor_write_not_implemented"],
      operations: ["local_visibility_task"]
    },
    supported_actions: ["local_visibility_task"]
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
    access_check_label: "połączenie potwierdzone",
    authorization_code_supported: true,
    authorization_code_supported_label: "tak",
    authorization_readiness_label: "gotowe do połączenia",
    pkce_s256_supported: true,
    pkce_s256_supported_label: "tak",
    secure_readiness_label: "bezpieczne połączenie gotowe",
    access_token_present: true,
    access_token_present_label: "token obecny",
    credential_readiness_label: "dostęp lokalny gotowy",
    evidence_ids: ["ev_refresh_refresh_localo_access_ready_test"],
    evidence_summary_label: "1 dowód źródłowy",
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
    missing_read_contract_summary_label: "5 brakujących danych",
    source_connectors: ["localo"],
    source_connector_labels: ["Localo"],
    evidence_ids: ["ev_refresh_refresh_localo_access_ready_test"],
    evidence_summary_label: "1 dowód źródłowy",
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
      allowed_evidence: ["mcp_initialize", "oauth_metadata", "local_access_presence"],
      allowed_evidence_labels: [
        "potwierdzenie dostępu Localo",
        "potwierdzenie autoryzacji",
        "potwierdzenie lokalnego dostępu"
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
      source_connector_labels: ["Localo"],
      evidence_ids: ["ev_refresh_refresh_localo_access_ready_test"],
      evidence_summary_label: "1 dowód źródłowy",
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
      source_connector_labels: ["Localo"],
      evidence_ids: ["ev_refresh_refresh_localo_access_ready_test"],
      evidence_summary_label: "1 dowód źródłowy",
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
      source_connector_labels: ["Localo"],
      evidence_ids: ["ev_refresh_refresh_localo_access_ready_test"],
      evidence_summary_label: "1 dowód źródłowy",
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
      status_label: "zakres danych niepodłączony",
      summary:
        "WILQ nie ma jeszcze rankingów, danych profilu firmy w Google, widoczności konkurencji ani recenzji z Localo.",
      diagnosis:
        "Brak tych danych oznacza brak lokalnej diagnozy marketingowej, nie brak problemu.",
      next_step:
        "Dodaj odczyt rankingów, profilu firmy w Google, konkurencji i recenzji zanim WILQ zaproponuje lokalne działania.",
      source_connectors: ["localo"],
      source_connector_labels: ["Localo"],
      evidence_ids: ["ev_refresh_refresh_localo_access_ready_test"],
      evidence_summary_label: "1 dowód źródłowy",
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
