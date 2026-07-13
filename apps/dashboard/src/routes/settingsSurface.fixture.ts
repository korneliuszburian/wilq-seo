import type { ConnectorRefreshRun, ConnectorStatus } from "@wilq/shared-schemas";

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

export const queuedSettingsRefreshRun: ConnectorRefreshRun = {
  id: "refresh-ga4-1",
  connector_id: "google_analytics_4",
  connector_label: "Google Analytics 4",
  mode: "vendor_read",
  status: "queued",
  status_label: "odczyt w kolejce",
  started_at: "2026-07-13T07:00:00Z",
  completed_at: null,
  evidence_ids: [],
  evidence_summary_label: "0 dowodów źródłowych",
  missing_credentials: [],
  checked_credentials: ["GOOGLE_ANALYTICS_PROPERTY_ID"],
  external_call_attempted: false,
  vendor_data_collected: false,
  metrics_persisted: false,
  metric_summary: {},
  summary: "Odczyt źródła w kolejce.",
  errors: [],
  redacted: true
};

export const completedSettingsRefreshRun: ConnectorRefreshRun = {
  ...queuedSettingsRefreshRun,
  status: "completed",
  status_label: "odczyt zakończony",
  completed_at: "2026-07-13T07:00:02Z",
  evidence_ids: ["ev_refresh_settings_ga4"],
  evidence_summary_label: "1 dowód źródłowy",
  external_call_attempted: true,
  vendor_data_collected: true,
  metrics_persisted: true,
  summary: "Odczyt źródła zakończony.",
};

export const eligibleSettingsConnectors: ConnectorStatus[] = settingsConnectors.map((connector) =>
  connector.id === "google_analytics_4"
    ? {
        ...connector,
        refresh_state: {
          ...connector.refresh_state,
          automatic_refresh: {
            ...connector.refresh_state.automatic_refresh,
            eligible: true,
            reason: "eligible_stale",
            reason_label: "Stare źródło kwalifikuje się do odczytu",
            safe_next_step: "Można bezpiecznie zlecić read-only refresh."
          }
        }
      }
    : connector
);

export const activeSettingsConnectors: ConnectorStatus[] = settingsConnectors.map((connector) =>
  connector.id === "google_analytics_4"
    ? {
        ...connector,
        refresh_state: {
          ...connector.refresh_state,
          state: "queued",
          state_label: "odczyt w kolejce",
          refresh_allowed: false,
          safe_next_step: "Odczyt jest w kolejce; poczekaj na wynik przed decyzją.",
          automatic_refresh: {
            ...connector.refresh_state.automatic_refresh,
            eligible: false,
            reason: "active_run",
            reason_label: "Odczyt źródła już trwa",
            safe_next_step: "Poczekaj na zakończenie aktywnego odczytu."
          }
        }
      }
    : connector
);

export const freshSettingsConnectors: ConnectorStatus[] = settingsConnectors.map((connector) =>
  connector.id === "google_analytics_4"
    ? {
        ...connector,
        freshness: { state: "fresh" },
        refresh_state: {
          ...connector.refresh_state,
          state: "ready",
          state_label: "odświeżone",
          refresh_allowed: true,
          safe_next_step: "Użyj ostatniego odczytu zgodnie ze świeżością.",
          automatic_refresh: {
            ...connector.refresh_state.automatic_refresh,
            eligible: false,
            reason: "not_stale",
            reason_label: "Źródło nie wymaga automatycznego odczytu",
            safe_next_step: "Użyj ostatniego odczytu zgodnie ze świeżością."
          }
        }
      }
    : connector
);
