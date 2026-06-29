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

  it("explains missing connector status as a readiness blocker", () => {
    const source = readFileSync("src/routes/GenericSurface.tsx", "utf8");

    expect(source).toContain(
      "WILQ nie ma statusu źródeł danych; odśwież integracje przed oceną gotowości."
    );
    expect(source).not.toMatch(/BlockerNotice message="Brak statusu/);
  });
});
