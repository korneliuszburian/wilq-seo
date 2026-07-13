import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { CompactRoutePanel, compactRouteConfig } from "./CompactRoutePanel";

describe("LegacyOperatingRoutes", () => {
  afterEach(() => {
    cleanup();
  });

  it("keeps the hidden search-terms route behind a safe Ads workflow", () => {
    const config = compactRouteConfig("/ads-doctor/search-terms");
    expect(config).toBeDefined();

    render(<CompactRoutePanel config={config!} />);

    expect(screen.getByText("ukryty placeholder")).toBeInTheDocument();
    expect(screen.getByText(/Otwórz Reklamy i pomiar/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Otwórz bezpieczny widok" })).toHaveAttribute(
      "href",
      "/ads-doctor"
    );
    expect(screen.getByText(/nie wolno twierdzić zmarnowanego budżetu/i)).toBeInTheDocument();
    expect(screen.queryByText("Evidence Registry")).not.toBeInTheDocument();
    expect(screen.queryByText("Connector Refresh Runs")).not.toBeInTheDocument();

    const ahrefsRouteSource = readFileSync("src/routes/AhrefsDiagnosticSurface.tsx", "utf8");
    expect(ahrefsRouteSource).toContain("decision.evidence_summary_label");
    expect(ahrefsRouteSource).toContain("contract.evidence_summary_label");
    expect(ahrefsRouteSource).not.toContain("formatAhrefsEvidenceCount");
  });
});
import { readFileSync } from "node:fs";
