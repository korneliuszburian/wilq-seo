import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GenericSurface } from "./GenericSurface";
import {
  completedSettingsRefreshRun,
  eligibleSettingsConnectors,
  queuedSettingsRefreshRun,
  settingsConnectors
} from "./settingsSurface.fixture";

describe("SettingsSourceRefresh", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("runs one read-only refresh and exposes the completed result", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/api/connectors") && !init?.method) {
        return Promise.resolve(Response.json(settingsConnectors));
      }
      if (url.endsWith("/api/connectors/google_analytics_4/refresh")) {
        return Promise.resolve(Response.json(queuedSettingsRefreshRun));
      }
      if (url.endsWith("/api/connectors/refresh-runs/refresh-ga4-1")) {
        return Promise.resolve(Response.json(completedSettingsRefreshRun));
      }
      return Promise.reject(new Error(`Unexpected settings request: ${url}`));
    });
    vi.stubGlobal("fetch", fetchMock);
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } }
    });

    render(
      <QueryClientProvider client={queryClient}>
        <GenericSurface routeName="/settings" />
      </QueryClientProvider>
    );

    const card = (await screen.findByRole("heading", { name: "Google Analytics 4" })).closest(
      "article"
    );
    expect(card).not.toBeNull();
    fireEvent.click(within(card as HTMLElement).getByRole("button", { name: "Odśwież dane" }));

    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some(([input, init]) =>
          String(input).endsWith("/api/connectors/google_analytics_4/refresh")
          && init?.method === "POST"
        )
      ).toBe(true)
    );
    expect(await screen.findByText("odczyt w kolejce")).toBeInTheDocument();
    expect(await screen.findByText(/Odczyt zakończony/)).toBeInTheDocument();
    expect(
      fetchMock.mock.calls.some(([input]) =>
        String(input).endsWith("/api/connectors/refresh-runs/refresh-ga4-1")
      )
    ).toBe(true);
  });

  it("keeps the source blocked and offers retry when polling fails", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/api/connectors") && !init?.method) {
        return Promise.resolve(Response.json(settingsConnectors));
      }
      if (url.endsWith("/api/connectors/google_analytics_4/refresh")) {
        return Promise.resolve(Response.json(queuedSettingsRefreshRun));
      }
      if (url.endsWith("/api/connectors/refresh-runs/refresh-ga4-1")) {
        return Promise.reject(new Error("refresh status unavailable"));
      }
      return Promise.reject(new Error(`Unexpected settings request: ${url}`));
    });
    vi.stubGlobal("fetch", fetchMock);
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } }
    });

    render(
      <QueryClientProvider client={queryClient}>
        <GenericSurface routeName="/settings" />
      </QueryClientProvider>
    );

    const card = (await screen.findByRole("heading", { name: "Google Analytics 4" })).closest(
      "article"
    );
    expect(card).not.toBeNull();
    fireEvent.click(within(card as HTMLElement).getByRole("button", { name: "Odśwież dane" }));
    expect(
      await screen.findByText(/Stan pozostaje niepotwierdzony; sprawdź dostęp albo spróbuj ponownie/)
    ).toBeInTheDocument();
    expect(within(card as HTMLElement).getByRole("button", { name: "Odśwież dane" })).toBeEnabled();
  });

  it("starts one automatic read-only refresh only when the API marks it eligible", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/api/connectors") && !init?.method) {
        return Promise.resolve(Response.json(eligibleSettingsConnectors));
      }
      if (url.endsWith("/api/connectors/google_analytics_4/refresh")) {
        return Promise.resolve(Response.json(queuedSettingsRefreshRun));
      }
      if (url.endsWith("/api/connectors/refresh-runs/refresh-ga4-1")) {
        return Promise.resolve(Response.json(completedSettingsRefreshRun));
      }
      return Promise.reject(new Error(`Unexpected settings request: ${url}`));
    });
    vi.stubGlobal("fetch", fetchMock);
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } }
    });

    render(
      <QueryClientProvider client={queryClient}>
        <GenericSurface routeName="/settings" />
      </QueryClientProvider>
    );

    expect(await screen.findByText("odczyt w kolejce")).toBeInTheDocument();
    expect(await screen.findByText(/Odczyt zakończony/)).toBeInTheDocument();
    expect(
      fetchMock.mock.calls.filter(([input]) =>
        String(input).endsWith("/api/connectors/google_analytics_4/refresh")
      )
    ).toHaveLength(1);
  });
});
