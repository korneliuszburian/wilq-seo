import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

const ROUTE_SOURCES = [
  "src/routes/Ga4DiagnosticSurface.tsx",
  "src/routes/BriefWorkflowSurface.tsx",
  "src/routes/LocaloDiagnosticSurface.tsx",
  "src/routes/AhrefsDiagnosticSurface.tsx",
  "src/routes/CustomSegmentsDiagnosticSurface.tsx"
];

describe("secondary route empty-state copy", () => {
  it("uses decision-limit language instead of bare brak placeholders", () => {
    const combined = ROUTE_SOURCES.map((path) => readFileSync(path, "utf8")).join("\n");
    expect(combined).not.toContain('empty="brak oceny gotowości pomiaru"');
    expect(combined).not.toContain('empty="brak oceny człowieka"');
    expect(combined).not.toContain('empty="brak dowodów źródłowych"');
    expect(combined).not.toContain('empty="brak źródeł danych"');
    expect(combined).not.toContain('empty="brak akcji do sprawdzenia"');
    expect(combined).toContain("sam dostęp do Localo nie jest rekomendacją");
    expect(combined).toContain("Ahrefs zostaje kontekstem, nie decyzją");
    expect(combined).toContain("nie oceniaj kampanii po tych danych");
    expect(combined).toContain("nie dodawaj segmentu bez review");
  });
});
