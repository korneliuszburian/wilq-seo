import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

describe("SocialPublisherSurface", () => {
  it("keeps social publishing review-only and history/dedupe blocked", () => {
    const routeSource = readFileSync("src/routes/SocialPublisherSurface.tsx", "utf8");
    expect(routeSource).toContain("Social jest tylko do review");
    expect(routeSource).toContain("Historia social blokuje brak powtórek");
    expect(routeSource).toContain("getSocialPublisherContextPack");
    expect(routeSource).toContain("history_audit_endpoint");
    expect(routeSource).toContain("Wymagany tylko spis metadanych");
    expect(routeSource).toContain("reviewSocialReuseProposal");
    expect(routeSource).toContain("Zatwierdź propozycję");
    expect(routeSource).toContain("Wyślij do poprawy");
    expect(routeSource).not.toContain("Social Publishing Focus");
    expect(routeSource).not.toContain("access token");
    expect(routeSource).not.toContain("ev_");
    expect(routeSource).not.toContain("act_");
  });
});
