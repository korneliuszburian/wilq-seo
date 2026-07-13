import type { ConnectorStatus } from "@wilq/shared-schemas";

export const settingsConnectors: ConnectorStatus[] = [
  {
    id: "google_ads",
    label: "Google Ads",
    status: "missing_credentials",
    status_label: "braki dostępu",
    product_scope: "production",
    product_scope_label: "Źródło produkcyjne",
    active_for_daily_work: true,
    configured: false,
    missing_credentials: ["GOOGLE_ADS_DEVELOPER_TOKEN"],
    missing_credentials_summary_label: "1 pole",
    available_credential_sources: [],
    credential_source_summary_label: "Nie ma źródeł konfiguracji; nie traktuj integracji jako gotowej",
    freshness: { state: "missing" },
    refresh_state: {
      state: "blocked",
      state_label: "odczyt zablokowany",
      refresh_allowed: false,
      safe_next_step: "Uzupełnij dostęp przed odczytem.",
      affected_decisions: ["ads_diagnostics", "command_center"],
      automatic_refresh: {
        eligible: false,
        reason: "missing_credentials",
        reason_label: "Brakuje dostępu do źródła",
        safe_next_step: "Uzupełnij credentials przed odczytem.",
        cooldown_seconds: 900
      }
    },
    health_check: "",
    supported_actions: []
  },
  {
    id: "google_analytics_4",
    label: "Google Analytics 4",
    status: "configured",
    status_label: "dostęp skonfigurowany",
    product_scope: "production",
    configured: true,
    missing_credentials: [],
    missing_credentials_summary_label: "Pola dostępu kompletne w tym sprawdzeniu",
    available_credential_sources: ["repo_env"],
    credential_source_summary_label: "1 źródło konfiguracji",
    active_for_daily_work: true,
    product_scope_label: "Ruch, zaangażowanie i jakość pomiaru.",
    freshness: { state: "stale" },
    refresh_state: {
      state: "stale",
      state_label: "wymaga odświeżenia",
      refresh_allowed: true,
      safe_next_step: "Uruchom bezpieczny odczyt źródła przed wnioskiem z danych.",
      affected_decisions: ["ga4_diagnostics", "command_center"],
      automatic_refresh: {
        eligible: false,
        reason: "cooldown",
        reason_label: "Odczyt źródła był uruchomiony niedawno",
        safe_next_step: "Poczekaj do końca okna ochronnego przed kolejnym odczytem.",
        cooldown_seconds: 900
      }
    },
    health_check: "",
    supported_actions: []
  }
];
