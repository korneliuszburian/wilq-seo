import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

describe("Ga4DiagnosticSurface", () => {
  it("keeps the GA4 measurement contract typed and review-only", () => {
    const routeSource = readFileSync("src/routes/Ga4DiagnosticSurface.tsx", "utf8");
    expect(routeSource).toContain("action.preview_cards");
    expect(routeSource).toContain("data.action_summary_label");
    expect(routeSource).toContain("data.evidence_summary_label");
    expect(routeSource).toContain("conversionReadiness.missing_read_contract_summary_label");
    expect(routeSource).toContain(
      "WILQ nie podał etykiety akcji; nie traktuj tej decyzji jako gotowej do działania"
    );
    expect(routeSource).not.toContain('empty="brak"');
    expect(routeSource).not.toContain("values={conversionReadiness.missing_read_contract_labels}");
    expect(routeSource).not.toContain("liczba akcji do sprawdzenia");
    expect(routeSource).not.toContain("action.payload.payload_preview");
    expect(routeSource).not.toContain("function formatGa4EvidenceCount");
    expect(routeSource).not.toContain("function formatGa4ActionCount");
  });
});
