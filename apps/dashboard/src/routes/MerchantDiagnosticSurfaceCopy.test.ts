import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

describe("MerchantDiagnosticSurface copy", () => {
  it("explains missing Merchant samples and counts as decision limits", () => {
    const source = readFileSync("src/routes/MerchantDiagnosticSurface.tsx", "utf8");

    expect(source).not.toContain('??\n    "brak"');
    expect(source).not.toContain('"brak próbek"');
    expect(source).not.toContain('"brak tytułów"');
    expect(source).not.toContain("brak wymaganej ścieżki rozwiązania");
    expect(source).toContain("licznik niepotwierdzony");
    expect(source).toContain("zakres niepotwierdzony");
    expect(source).toContain("WILQ nie podał próbek produktów; sprawdź Merchant przed edycją");
    expect(source).toContain("WILQ nie podał tytułów próbek; identyfikuj produkt w Merchant przed oceną");
  });
});
