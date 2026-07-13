import { readFileSync } from "node:fs";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { localoDiagnostics } from "./localoDiagnostics.fixture";
import { LocaloDiagnosticSurface } from "./LocaloDiagnosticSurface";

vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return { ...actual, getLocaloDiagnostics: vi.fn().mockResolvedValue(localoDiagnostics) };
});

describe("LocaloDiagnosticSurface", () => {
  it("shows access state and blocks local recommendations without ranking proof", async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={queryClient}>
        <LocaloDiagnosticSurface />
      </QueryClientProvider>
    );

    await waitFor(() => expect(screen.getByRole("heading", { name: "Localo" })).toBeInTheDocument());
    expect(screen.getByText("Status Localo i widoczność lokalna")).toBeInTheDocument();
    expect(screen.getByText(/Brak danych Localo o rankingach/)).toBeInTheDocument();
    expect(screen.getByText(/nie obiecuje poprawy widoczności/)).toBeInTheDocument();
    expect(screen.queryByText("localo")).not.toBeInTheDocument();
  });

  it("keeps local visibility blockers and technical details API-owned", () => {
    const routeSource = readFileSync("src/routes/LocaloDiagnosticSurface.tsx", "utf8");
    expect(routeSource).toContain("data.operator_summary.missing_read_contract_summary_label");
    expect(routeSource).not.toContain('empty="brak"');
    expect(routeSource).not.toContain("Localo / {decision.decision_type_label} / {decision.priority_label}");
    expect(routeSource).not.toContain("data.operator_summary.missing_read_contracts.length");
  });
});
