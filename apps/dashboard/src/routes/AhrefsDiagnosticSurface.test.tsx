import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

describe("AhrefsDiagnosticSurface", () => {
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
