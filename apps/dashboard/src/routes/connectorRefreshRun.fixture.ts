import type { ConnectorRefreshRun } from "../lib/api";

export const connectorRefreshRun = {
  id: "refresh_google_ads_test",
  connector_id: "google_ads",
  connector_label: "Google Ads",
  mode: "status_probe",
  status: "completed",
  status_label: "zakończony",
  started_at: "2026-06-17T10:00:00Z",
  completed_at: "2026-06-17T10:00:01Z",
  evidence_ids: ["ev_connector_google_ads_status", "ev_refresh_refresh_google_ads_test"],
  evidence_summary_label: "2 dowody źródłowe",
  missing_credentials: [],
  checked_credentials: ["GOOGLE_ADS_DEVELOPER_TOKEN"],
  external_call_attempted: false,
  vendor_data_collected: false,
  metrics_persisted: true,
  metric_summary: { clicks: 12, impressions: 120, api: "google_ads_probe" },
  summary: "Connector google_ads status probe completed.",
  errors: [],
  redacted: true
} satisfies ConnectorRefreshRun;
