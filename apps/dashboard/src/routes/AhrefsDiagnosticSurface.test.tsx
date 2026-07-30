import { readFileSync } from "node:fs";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ahrefsDiagnostics } from "./ahrefsDiagnostics.fixture";
import { AhrefsDiagnosticSurface } from "./AhrefsDiagnosticSurface";

vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return { ...actual, getAhrefsDiagnostics: vi.fn().mockResolvedValue(ahrefsDiagnostics) };
});

describe("AhrefsDiagnosticSurface", () => {
  it("shows only confirmed Ahrefs facts when the read is partial", async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={queryClient}>
        <AhrefsDiagnosticSurface />
      </QueryClientProvider>
    );

    await waitFor(() => expect(screen.getByRole("heading", { name: "Ahrefs" })).toBeInTheDocument());
    expect(screen.getByText("Dane częściowe")).toBeInTheDocument();
    expect(screen.getByText("autorytet domeny: 90")).toBeInTheDocument();
    expect(screen.getByText(/obejmują tylko zakończone etapy/)).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Etapy odczytu Ahrefs" })).not.toBeInTheDocument();
    expect(screen.queryByText("Luki SEO z Ahrefs")).not.toBeInTheDocument();
    expect(screen.queryByText("ahrefs")).not.toBeInTheDocument();
  });

  it("keeps authority and gap diagnostics evidence-first", () => {
    const routeSource = readFileSync("src/routes/AhrefsDiagnosticSurface.tsx", "utf8");
    expect(routeSource).toContain("contract.missing_read_contract_summary_label");
    expect(routeSource).toContain("contract.blocked_claim_summary_label");
    expect(routeSource).not.toContain('empty="brak"');
    expect(routeSource).not.toContain(
      'Ahrefs / {decision.decision_type_label || "decyzja"} / {decision.priority_label}'
    );
    expect(routeSource).not.toContain("contract.missing_read_contracts.length");
    expect(routeSource).not.toContain("contract.blocked_claims.length");
  });
});
