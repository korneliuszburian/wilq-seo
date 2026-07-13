import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";

import { GenericSurface } from "./GenericSurface";

function renderGenericSurface(routeName: string) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } }
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <GenericSurface routeName={routeName} />
    </QueryClientProvider>
  );
}

describe("GenericSurface", () => {
  afterEach(() => {
    cleanup();
  });

  it("does not render the old registry fallback sections", () => {
    renderGenericSurface("/security");

    expect(screen.getByRole("heading", { name: "Bezpieczeństwo" })).toBeInTheDocument();
    expect(screen.queryByText("Evidence Registry")).not.toBeInTheDocument();
    expect(screen.queryByText("Connector Refresh Runs")).not.toBeInTheDocument();
    expect(screen.queryByText("Connector Status")).not.toBeInTheDocument();
    expect(screen.queryByText("Opportunities")).not.toBeInTheDocument();
    expect(screen.queryByText("Actions")).not.toBeInTheDocument();
    expect(screen.queryByText("Expert Rules")).not.toBeInTheDocument();
  });

  it("renders compact blockers for secondary utility routes", () => {
    renderGenericSurface("/google-sheets");
    expect(screen.getByRole("heading", { name: "Google Sheets" })).toBeInTheDocument();
    expect(screen.getByText("Status widoku")).toBeInTheDocument();
    expect(screen.getByText(/nie ma zatwierdzonego zakresu eksportu/i)).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "OPPORTUNITIES" })).not.toBeInTheDocument();
    expect(screen.queryByText("Connector Refresh Runs")).not.toBeInTheDocument();
    expect(screen.queryByText(/GOOGLE_ADS \/ PREPARE/)).not.toBeInTheDocument();
    expect(screen.queryByText(/vendor_read/)).not.toBeInTheDocument();

    cleanup();
    renderGenericSurface("/security");
    expect(screen.getByRole("heading", { name: "Bezpieczeństwo" })).toBeInTheDocument();
    expect(screen.getByText("Status widoku")).toBeInTheDocument();
    expect(screen.getByText(/nie ma pełnego dashboardu bezpieczeństwa/i)).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "OPPORTUNITIES" })).not.toBeInTheDocument();
    expect(screen.queryByText("Evidence Registry")).not.toBeInTheDocument();
    expect(screen.queryByText(/CONNECTOR_REFRESH_RUN/)).not.toBeInTheDocument();
  });

  it("explains missing connector status as a readiness blocker", () => {
    const source = readFileSync("src/routes/GenericSurface.tsx", "utf8");

    expect(source).toContain(
      "WILQ nie ma statusu źródeł danych; odśwież integracje przed oceną gotowości."
    );
    expect(source).not.toMatch(/BlockerNotice message="Brak statusu/);
  });

  it("explains hidden Ads placeholders with a safe workflow route", () => {
    renderGenericSurface("/ads-doctor/scaling");

    expect(screen.getByRole("heading", { name: "Skalowanie Ads" })).toBeInTheDocument();
    expect(screen.getByText("zablokowane do czasu reguł skalowania")).toBeInTheDocument();
    expect(screen.getByText(/Skalowanie zostaje review-only/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Otwórz bezpieczny widok" })).toHaveAttribute(
      "href",
      "/ads-doctor"
    );
    expect(screen.queryByText("Evidence Registry")).not.toBeInTheDocument();
  });

  it("defers knowledge catalogs until the operator opens their disclosure", () => {
    const source = readFileSync("src/routes/GenericSurface.tsx", "utf8");

    expect(source).toContain('enabled: routeKind === "knowledge" && showKnowledgeCards');
    expect(source).toContain('enabled: routeKind === "knowledge" && showKnowledgePlaybooks');
    expect(source).toContain("setShowKnowledgeCards");
  });
});
