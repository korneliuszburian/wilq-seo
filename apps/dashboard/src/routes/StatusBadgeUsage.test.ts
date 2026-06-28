import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

describe("StatusBadge state usage", () => {
  it("keeps API labels as labels, not visual state values", () => {
    const routeSources = [
      "src/routes/ActionObjectPanels.tsx",
      "src/routes/DetailPanels.tsx",
      "src/routes/Ga4DiagnosticSurface.tsx",
      "src/routes/KnowledgePanels.tsx",
      "src/routes/MerchantDiagnosticSurface.tsx"
    ].map((path) => readFileSync(path, "utf8"));

    for (const source of routeSources) {
      expect(source).not.toMatch(
        /<StatusBadge\s+value=\{[^}]*\.(status_label|risk_label|validation_status_label)\}/
      );
      expect(source).not.toMatch(
        /<StatusBadge\s+value=\{[^}]*\b(status_label|risk_label|validation_status_label)\}/
      );
    }
  });
});
