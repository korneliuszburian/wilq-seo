import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { Evidence } from "../lib/api";
import { getEvidenceById } from "../lib/api";
import { EvidenceDetailSurface } from "./DetailPanels";

vi.mock("../lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../lib/api")>()),
  getEvidenceById: vi.fn()
}));

const evidence: Evidence = {
  id: "ev_refresh_merchant_feed",
  title_label: "Dowód z Merchant Center",
  source_connector: "google_merchant_center",
  source_connector_label: "Merchant Center",
  source_type: "vendor_read",
  source_type_label: "odczyt źródła danych",
  source_id: "refresh_google_merchant_center",
  collected_at: "2026-07-12T17:29:28Z",
  freshness: { state: "fresh", notes: null },
  freshness_label: "świeże dane",
  summary: "Merchant Center product-file diagnostics collected sanitized product issue counters.",
  trace_summary_label: "3 dowody źródłowe",
  raw_ref: null
};

describe("EvidenceDetailRoute", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("renders a marketer-readable evidence trace with technical details disclosed", async () => {
    vi.mocked(getEvidenceById).mockResolvedValue(evidence);
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={queryClient}>
        <EvidenceDetailSurface evidenceId={evidence.id} />
      </QueryClientProvider>
    );

    expect(await screen.findByRole("heading", { name: "Dowód z Merchant Center" })).toBeInTheDocument();
    expect(screen.getByText(evidence.summary)).toBeInTheDocument();
    expect(screen.getByText("Źródło: Merchant Center")).toBeInTheDocument();
    expect(screen.getByText("Typ źródła: odczyt źródła danych")).toBeInTheDocument();
    expect(screen.getByText("Świeżość: świeże dane")).toBeInTheDocument();
    expect(screen.queryByText("Źródło: google_merchant_center")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: evidence.id })).not.toBeInTheDocument();
    expect(screen.queryByText(/ID dowodu/)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Pokaż szczegóły techniczne dowodu" }));
    expect(screen.getByText(/Klucz dowodu w WILQ:/)).toBeInTheDocument();
    expect(screen.queryByText(/ID dowodu/)).not.toBeInTheDocument();
  });
});
