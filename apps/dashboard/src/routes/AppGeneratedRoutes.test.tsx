import { existsSync, readFileSync } from "node:fs";

import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App, createWilqQueryClient, createWilqRouter } from "./App";

vi.mock("./AdsDoctorSurface", () => ({
  AdsDoctorSurface: () => (
    <main data-testid="dedicated-ads-doctor">Dedykowana diagnostyka Ads</main>
  )
}));

describe("generated route rendering", () => {
  afterEach(() => {
    cleanup();
  });

  it("does not retain the retired brief fallback branch or module", () => {
    const appSource = readFileSync("src/routes/App.tsx", "utf8");
    const retiredComponent = ["Brief", "Workflow", "Surface"].join("");
    const retiredConfig = ["brief", "Surface", "Configs"].join("");

    expect(appSource).not.toContain(retiredComponent);
    expect(appSource).not.toContain(retiredConfig);
    expect(existsSync(`src/routes/${retiredComponent}.tsx`)).toBe(false);
  });

  it("renders the dedicated Ads doctor for its generated route", async () => {
    const client = createWilqQueryClient({
      defaultOptions: { queries: { retry: false } }
    });

    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/ads-doctor", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    expect(await screen.findByTestId("dedicated-ads-doctor")).toHaveTextContent(
      "Dedykowana diagnostyka Ads"
    );
  });
});
