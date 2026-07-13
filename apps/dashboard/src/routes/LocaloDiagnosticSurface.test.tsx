import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

describe("LocaloDiagnosticSurface", () => {
  it("keeps local visibility blockers and technical details API-owned", () => {
    const routeSource = readFileSync("src/routes/LocaloDiagnosticSurface.tsx", "utf8");
    expect(routeSource).toContain("data.operator_summary.missing_read_contract_summary_label");
    expect(routeSource).not.toContain('empty="brak"');
    expect(routeSource).not.toContain("Localo / {decision.decision_type_label} / {decision.priority_label}");
    expect(routeSource).not.toContain("data.operator_summary.missing_read_contracts.length");
  });
});
