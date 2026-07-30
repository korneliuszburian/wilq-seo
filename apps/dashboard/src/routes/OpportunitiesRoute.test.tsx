import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./CommandCenterRoute", () => ({
  CommandCenter: () => <h1>Dzisiaj</h1>
}));

import { App, createWilqQueryClient, createWilqRouter } from "./App";

describe("Legacy opportunities routes", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  for (const initialPath of [
    "/opportunities",
    "/opportunities/opp_decision_review_ads_campaign_metrics"
  ]) {
    it(`redirects ${initialPath} to the daily work order without reading opportunities`, async () => {
      const appRouter = createWilqRouter({ initialPath, defaultPendingMinMs: 0 });
      const client = createWilqQueryClient({
        defaultOptions: { queries: { gcTime: Infinity, retry: false } }
      });

      render(<App appRouter={appRouter} client={client} />);

      await waitFor(() => expect(appRouter.state.location.pathname).toBe("/command-center"));
      expect(screen.getByRole("heading", { name: "Dzisiaj" })).toBeInTheDocument();
      expect(globalThis.fetch).not.toHaveBeenCalled();
      client.clear();
    });
  }
});
