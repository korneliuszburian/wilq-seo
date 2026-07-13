import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GenericSurface } from "./GenericSurface";
import { settingsConnectors } from "./settingsSurface.fixture";

function renderSettingsSurface() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } }
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <GenericSurface routeName="/settings" />
    </QueryClientProvider>
  );
}

describe("SettingsSurface", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("shows source health, decision blockers and hides technical payloads by default", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(Response.json(settingsConnectors))
    );

    renderSettingsSurface();

    expect(await screen.findByRole("heading", { name: "Źródła" })).toBeInTheDocument();
    expect(
      screen.getByText("Zdrowie źródeł, aktualność danych i dostęp wpływają na jakość decyzji.")
    ).toBeInTheDocument();
    expect(screen.getByText("brak dostępu")).toBeInTheDocument();
    expect(screen.getByText("wymagają odświeżenia")).toBeInTheDocument();
    expect(screen.getByText("Co blokuje pracę")).toBeInTheDocument();
    expect(screen.getByText(/Brakuje dostępu do Google Ads/)).toBeInTheDocument();
    expect(screen.getByText(/1 źródło wymaga odświeżenia przed oceną wyników/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Dostęp do źródeł" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Wpływ braków na decyzje" })).toBeInTheDocument();
    expect(screen.getByText("Eksport zablokowany")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Pokaż szczegóły techniczne źródeł" })).toBeInTheDocument();
    expect(screen.queryByText("GOOGLE_ADS_DEVELOPER_TOKEN")).not.toBeInTheDocument();
    expect(screen.queryByText("google_ads")).not.toBeInTheDocument();
    expect(screen.queryByText("Evidence Registry")).not.toBeInTheDocument();
  });
});
