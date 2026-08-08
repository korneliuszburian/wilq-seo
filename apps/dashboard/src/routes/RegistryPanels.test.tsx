import { readFileSync } from "node:fs";

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { ConnectorStatus } from "../lib/api";
import { ConnectorGrid } from "./RegistryPanels";

describe("RegistryPanels", () => {
  it("connector cards summarize access without raw ids or credential names", () => {
    render(
      <ConnectorGrid
        connectors={[
          ({
            id: "google_ads",
            label: "Google Ads",
            status: "missing_credentials",
            status_label: "brakuje dostępu",
            product_scope: "production",
            product_scope_label: "aktywny zakres WILQ",
            active_for_daily_work: true,
            configured: false,
            missing_credentials: ["GOOGLE_ADS_DEVELOPER_TOKEN"],
            missing_credentials_summary_label: "1 pole",
            available_credential_sources: ["repo_env"],
            credential_source_summary_label: "1 źródło",
            freshness: { state: "missing" },
            refresh_state: {
              state: "blocked",
              state_label: "odczyt zablokowany",
              refresh_allowed: false,
              last_run_id: null,
              last_run_status: "blocked",
              last_run_started_at: null,
              last_run_completed_at: null,
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
            risk_notes:
              "Akcje Ads służą obecnie wyłącznie do przygotowania i sprawdzenia; brak adaptera zapisu do Google Ads.",
            health_check: "credential_presence",
            capabilities: {
              read: true,
              write: false,
              read_adapter: "google_ads_api",
              mutation_adapter: null,
              action_scope: "review_only",
              blockers: ["vendor_write_not_implemented"],
              operations: []
            },
            supported_actions: []
          } satisfies ConnectorStatus)
        ]}
      />
    );

    expect(screen.getByText("Google Ads")).toBeInTheDocument();
    expect(screen.getByText("Źródło danych sprawdzane przez WILQ.")).toBeInTheDocument();
    expect(
      screen.getByText("Akcje: przygotowanie i review, bez zapisu do systemu zewnętrznego.")
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Zakres i bezpieczeństwo: Akcje Ads służą obecnie wyłącznie do przygotowania i sprawdzenia; brak adaptera zapisu do Google Ads."
      )
    ).toBeInTheDocument();
    expect(screen.getByText("Brakujące ustawienia dostępu")).toBeInTheDocument();
    expect(screen.getByText("1 pole")).toBeInTheDocument();
    expect(screen.getByText("Źródła konfiguracji: 1 źródło")).toBeInTheDocument();
    expect(screen.queryByText("google_ads")).not.toBeInTheDocument();
    expect(screen.queryByText("GOOGLE_ADS_DEVELOPER_TOKEN")).not.toBeInTheDocument();
    expect(screen.queryByText("repo_env")).not.toBeInTheDocument();
    expect(screen.queryByText("Brakujące credentiale")).not.toBeInTheDocument();

    const source = readFileSync("src/routes/RegistryPanels.tsx", "utf8");
    expect(source).not.toContain("connector.missing_credentials.length, \"pole\"");
    expect(source).not.toContain("connector.available_credential_sources.length,");
  });

});
