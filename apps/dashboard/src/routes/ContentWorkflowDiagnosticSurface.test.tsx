import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

describe("ContentWorkflowDiagnosticSurface", () => {
  it("keeps the primary content workflow boundary API-owned", () => {
    const routeSource = readFileSync("src/routes/ContentWorkflowSurface.tsx", "utf8");
    expect(routeSource).toContain("ContentPageWorkbench");
    expect(routeSource).toContain("Treści: praca nad stroną");
    expect(routeSource).toContain("Aktualna strona");
    expect(routeSource).toContain("Sygnały i braki");
    expect(routeSource).toContain("Dev draft / ACF");
    expect(routeSource).toContain("Tekst sekcji do szkicu");
    expect(routeSource).toContain("Podgląd sekcji na devie");
    expect(routeSource).toContain("section_overrides");
    expect(routeSource).toContain("source_public_url");
    expect(routeSource).toContain("wordpress_section_headings");
    expect(routeSource).toContain("selectDevPage");
    expect(routeSource).toContain("ekologus.dev.proudsite.pl");
    expect(routeSource).not.toContain("ContentPlannerMockupViewport");
    expect(routeSource).not.toContain("ForbiddenClaimsStrip");
    expect(routeSource).not.toContain('empty="brak"');
    expect(routeSource).not.toContain("Stan danych treści");
    expect(routeSource).not.toContain("WILQ widzi 2 kandydat");
    expect(routeSource).not.toContain("formatContentEvidenceCount");
    expect(routeSource).not.toContain("formatContentActionCount");
  });

  it("keeps expanded workflow language Polish and draft-only", () => {
    const routeSource = readFileSync("src/routes/ContentWorkflowSurface.tsx", "utf8");
    expect(routeSource).toContain("Szczegóły workflow, kolejka i audyt techniczny");
    expect(routeSource).toContain("WorkflowStepsList");
    expect(routeSource).toContain('<FactTile label="Publikacja" value="zablokowana" />');
    expect(routeSource).toContain("Piszemy i układamy szkic na ekologus.dev.proudsite.pl");
    expect(routeSource).toContain("Publiczna strona pozostaje punktem");
    expect(routeSource).not.toContain("Zapytania/URL");
    expect(routeSource).not.toContain("GSC↔WP");
    expect(routeSource).not.toContain("Ahrefs↔WP");
    expect(routeSource).not.toContain("WordPress: inventory protection");
    expect(routeSource).not.toContain("Payload: 4 checked items");
    expect(routeSource).not.toContain("wersja robocza istniejącej treści / draft");
  });
});
