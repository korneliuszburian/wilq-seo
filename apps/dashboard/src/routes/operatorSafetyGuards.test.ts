import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

const readSource = (path: string) => readFileSync(path, "utf8");

const readSources = (paths: string[]) => paths.map(readSource).join("\n");

describe("operator safety copy guards", () => {
  it("keeps Ads empty states framed as decision limits", () => {
    const source = readSources([
      "src/routes/AdsDoctorSurface.tsx",
      "src/components/AdsOverviewPanels.tsx",
      "src/components/AdsMetricEvidencePanel.tsx",
      "src/components/AdsOperatorSummaryPanels.tsx",
      "src/components/AdsBudgetRecommendationPanels.tsx",
      "src/components/AdsBusinessReadinessPanels.tsx",
      "src/lib/adsLabels.ts"
    ]);

    expect(source).not.toContain('empty="brak');
    expect(source).toContain("nie oceniaj skuteczności z tego panelu");
    expect(source).toContain("nie traktuj tego jako rekomendacji Ads");
    expect(source).toContain("nie wykonuj zmiany bez review");
    expect(source).toContain("nie automatyzuj decyzji");
    expect(source).toContain("bez ostatniego odczytu; nie oceniaj trendu");
    expect(source).toContain("nie ma podglądu zmian; nie zapisuj zmiany");
    expect(source).toContain("metryki kampanii niepotwierdzone; nie oceniaj wpływu");
  });

  it("keeps Merchant sample and count gaps framed as decision limits", () => {
    const source = readSource("src/routes/MerchantDiagnosticSurface.tsx");

    expect(source).not.toContain('??\n    "brak"');
    expect(source).not.toContain('"brak próbek"');
    expect(source).not.toContain('"brak tytułów"');
    expect(source).not.toContain("brak wymaganej ścieżki rozwiązania");
    expect(source).toContain("licznik niepotwierdzony");
    expect(source).toContain("zakres niepotwierdzony");
    expect(source).toContain("WILQ nie podał próbek produktów; sprawdź Merchant przed edycją");
    expect(source).toContain(
      "WILQ nie podał tytułów próbek; identyfikuj produkt w Merchant przed oceną"
    );
  });

  it("keeps secondary diagnostic empty states tied to safe action limits", () => {
    const source = readSources([
      "src/routes/Ga4DiagnosticSurface.tsx",
      "src/routes/BriefWorkflowSurface.tsx",
      "src/routes/LocaloDiagnosticSurface.tsx",
      "src/routes/AhrefsDiagnosticSurface.tsx",
      "src/routes/CustomSegmentsDiagnosticSurface.tsx",
      "src/components/AdsCustomSegmentPanels.tsx"
    ]);

    expect(source).not.toContain('empty="brak oceny gotowości pomiaru"');
    expect(source).not.toContain('empty="brak oceny człowieka"');
    expect(source).not.toMatch(/empty="brak (dowodów|źródeł|akcji)/);
    expect(source).toContain("sam dostęp do Localo nie jest rekomendacją");
    expect(source).toContain("Ahrefs zostaje kontekstem, nie decyzją");
    expect(source).toContain("nie oceniaj kampanii po tych danych");
    expect(source).toContain("nie dodawaj segmentu bez review");
  });

  it("keeps smaller diagnostics on the shared diagnostic page shell proof path", () => {
    const diagnosticSources = [
      readSource("src/routes/LocaloDiagnosticSurface.tsx"),
      readSource("src/routes/Ga4DiagnosticSurface.tsx")
    ];
    const shellSource = readSource("src/components/DiagnosticSurfaceShell.tsx");

    for (const source of diagnosticSources) {
      expect(source).toContain("<DiagnosticPage");
      expect(source).not.toContain("diagnostics.isLoading");
      expect(source).not.toContain("DiagnosticSurfaceUnavailable");
    }
    expect(shellSource).toContain("export function DiagnosticPage");
    expect(shellSource).toContain("query.isLoading");
    expect(shellSource).toContain("DiagnosticSurfaceUnavailable");
  });

  it("keeps Tactical Queue evidence and action gaps explicit", () => {
    const source = readSource("src/routes/TacticalQueuePanel.tsx");

    expect(source).not.toContain('empty="brak dowodów do pokazania"');
    expect(source).not.toMatch(/empty="brak akcji/);
    expect(source).toContain("nie traktuj tej pozycji jako rekomendacji");
    expect(source).toContain("następny krok musi pozostać ręczną oceną");
  });

  it("keeps operating workflow outcomes away from bare brak placeholders", () => {
    const source = readSource("src/routes/OperatingRouteSurfaces.tsx");

    expect(source).not.toContain('WILQ ma {count || "brak"}');
    expect(source).not.toContain("WILQ ma brak");
    expect(source).toContain("Nie traktuj tego procesu jak gotowej decyzji");
  });

  it("keeps API labels out of StatusBadge visual state values", () => {
    const routeSources = [
      "src/routes/ActionPanels.tsx",
      "src/routes/DetailPanels.tsx",
      "src/routes/Ga4DiagnosticSurface.tsx",
      "src/routes/KnowledgePanels.tsx",
      "src/routes/MerchantDiagnosticSurface.tsx"
    ].map(readSource);

    for (const source of routeSources) {
      expect(source).not.toMatch(
        /<StatusBadge\s+value=\{[^}]*\.(status_label|risk_label|validation_status_label)\}/
      );
      expect(source).not.toMatch(
        /<StatusBadge\s+value=\{[^}]*\b(status_label|risk_label|validation_status_label)\}/
      );
      expect(source).not.toMatch(
        /<StatusBadge\s+value=\{[^}]*(source_connector_label|source_type_label|domain_label)[^}]*\}/
      );
    }
  });
});
