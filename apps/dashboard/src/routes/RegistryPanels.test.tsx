import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { ConnectorRefreshRun, ConnectorStatus, Evidence } from "../lib/api";
import { ConnectorGrid, ConnectorRefreshRunList, EvidenceList } from "./RegistryPanels";

describe("RegistryPanels", () => {
  it("connector cards summarize access without raw ids or credential names", () => {
    render(
      <ConnectorGrid
        connectors={[
          ({
            id: "google_ads",
            label: "Google Ads",
            status: "missing_credentials",
            configured: false,
            missing_credentials: ["GOOGLE_ADS_DEVELOPER_TOKEN"],
            available_credential_sources: ["repo_env"],
            freshness: { state: "missing" },
            supported_actions: []
          } satisfies ConnectorStatus)
        ]}
      />
    );

    expect(screen.getByText("Google Ads")).toBeInTheDocument();
    expect(screen.getByText("Źródło danych sprawdzane przez WILQ.")).toBeInTheDocument();
    expect(screen.getByText("Brakujące ustawienia dostępu")).toBeInTheDocument();
    expect(screen.getByText("1 pole")).toBeInTheDocument();
    expect(screen.getByText("Źródła konfiguracji: 1 źródło")).toBeInTheDocument();
    expect(screen.queryByText("google_ads")).not.toBeInTheDocument();
    expect(screen.queryByText("GOOGLE_ADS_DEVELOPER_TOKEN")).not.toBeInTheDocument();
    expect(screen.queryByText("repo_env")).not.toBeInTheDocument();
    expect(screen.queryByText("Brakujące credentiale")).not.toBeInTheDocument();
  });

  it("evidence cards hide raw source identifiers from the list view", () => {
    render(
      <EvidenceList
        evidenceItems={[
          ({
            id: "ev_connector_google_ads_status",
            source_connector: "google_ads",
            source_type: "connector_refresh",
            source_id: "refresh_google_ads_test",
            collected_at: "2026-06-17T10:00:00Z",
            freshness: { state: "fresh" },
            summary: "Google Ads odczytany z sanitizowanym podsumowaniem.",
            raw_ref: null
          } satisfies Evidence)
        ]}
      />
    );

    expect(screen.getByText("Dowód z WILQ")).toBeInTheDocument();
    expect(
      screen.getByText("Zebrany fakt użyty do decyzji. Pełne identyfikatory zostają w śladzie audytu.")
    ).toBeInTheDocument();
    expect(screen.queryByText("ev_connector_google_ads_status")).not.toBeInTheDocument();
    expect(screen.queryByText(/google_ads \/ connector_refresh/)).not.toBeInTheDocument();
  });

  it("connector refresh cards summarize counts instead of raw run details", () => {
    render(
      <ConnectorRefreshRunList
        runs={[
          ({
            id: "refresh_google_ads_test",
            connector_id: "google_ads",
            mode: "vendor_read",
            status: "completed",
            summary: "Odczyt Google Ads zakończony.",
            evidence_ids: ["ev_connector_google_ads_status", "ev_refresh_refresh_google_ads_test"],
            missing_credentials: [],
            checked_credentials: [],
            started_at: "2026-06-17T10:00:00Z",
            completed_at: "2026-06-17T10:01:00Z",
            metric_summary: {
              clicks: 12,
              impressions: 120,
              api: "google_ads_probe"
            },
            vendor_data_collected: true,
            external_call_attempted: true,
            errors: [],
            redacted: true
          } satisfies ConnectorRefreshRun)
        ]}
      />
    );

    expect(screen.getByText("Odczyt źródła danych")).toBeInTheDocument();
    expect(screen.getByText("Dowody: 2 ID")).toBeInTheDocument();
    expect(screen.getByText("Metryki: 3 wartości")).toBeInTheDocument();
    expect(screen.queryByText("refresh_google_ads_test")).not.toBeInTheDocument();
    expect(screen.queryByText("google_ads")).not.toBeInTheDocument();
    expect(screen.queryByText("vendor_read")).not.toBeInTheDocument();
    expect(screen.queryByText(/clicks=12/)).not.toBeInTheDocument();
  });
});
