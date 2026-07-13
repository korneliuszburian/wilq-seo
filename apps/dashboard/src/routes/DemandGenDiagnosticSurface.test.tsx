import { readFileSync } from "node:fs";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { demandGenDiagnostics } from "./demandGenDiagnostics.fixture";
import { DemandGenDiagnosticSurface } from "./DemandGenDiagnosticSurface";

vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return { ...actual, getDemandGenDiagnostics: vi.fn().mockResolvedValue(demandGenDiagnostics) };
});

describe("DemandGenDiagnosticSurface", () => {
  it("blocks a Demand Gen plan when the channel is absent from evidence", async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={queryClient}>
        <DemandGenDiagnosticSurface />
      </QueryClientProvider>
    );

    await waitFor(() => expect(screen.getByRole("heading", { name: "Demand Gen" })).toBeInTheDocument());
    expect(screen.getByText("Sprawdzenie Demand Gen")).toBeInTheDocument();
    expect(screen.getByText("Co marketer ma wiedzieć przed planem Demand Gen")).toBeInTheDocument();
    expect(screen.getByText(/nie ma kampanii Demand Gen ani Discovery/)).toBeInTheDocument();
    expect(screen.getByText("Podgląd gotowości Demand Gen")).toBeInTheDocument();
  });

  it("keeps Demand Gen readiness typed, evidence-backed and review-only", () => {
    const routeSource = readFileSync("src/routes/DemandGenDiagnosticSurface.tsx", "utf8");
    expect(routeSource).toContain("data.preview_cards");
    expect(routeSource).toContain("data.action_summary_label");
    expect(routeSource).toContain("row.evidence_summary_label");
    expect(routeSource).toContain("row.landing_page_label");
    expect(routeSource).toContain("row.source_medium_label");
    expect(routeSource).toContain("row.advertising_channel_type_label");
    expect(routeSource).toContain("row.campaign_status_label");
    expect(routeSource).toContain("row.clicks_label");
    expect(routeSource).toContain("row.impressions_label");
    expect(routeSource).toContain("row.cost_label");
    expect(routeSource).toContain("row.conversions_label");
    expect(routeSource).toContain("row.active_users_label");
    expect(routeSource).toContain("row.sessions_label");
    expect(routeSource).toContain("row.engagement_rate_label");
    expect(routeSource).not.toContain("{row.landing_page} / {row.source_medium");
    expect(routeSource).not.toContain('row.clicks ?? "brak"');
    expect(routeSource).not.toContain('row.impressions ?? "brak"');
    expect(routeSource).not.toContain('row.conversions ?? "brak"');
    expect(routeSource).not.toContain('row.active_users ?? "brak"');
    expect(routeSource).not.toContain('row.sessions ?? "brak"');
    expect(routeSource).not.toContain("function adsCost");
    expect(routeSource).not.toContain("function adsPercent");
    expect(routeSource).not.toContain("data.campaign_channel_labels[channel] ?? channel");
    expect(routeSource).not.toContain("formatDemandGenIdCount");
    expect(routeSource).not.toContain("formatDemandGenEvidenceCount");
    expect(routeSource).not.toContain("data.payload_preview[0]");
    expect(routeSource).not.toContain("row.advertising_channel_type ??");
    expect(routeSource).not.toContain("row.campaign_status ??");
    expect(routeSource).not.toContain("row.reason_label ?? row.reason");
    expect(routeSource).not.toContain("Record<string, unknown>");
    expect(routeSource).not.toContain("stringArray(");
  });
});
