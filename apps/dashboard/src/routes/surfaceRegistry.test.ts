import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import {
  generatedSurfaceRoutes,
  primarySurfaceRoutes,
  secondarySurfaceRoutes,
  surfaceRoutes
} from "./surfaceRegistry";

describe("surface registry", () => {
  it("keeps every surface path unique and explicitly classified", () => {
    const paths = surfaceRoutes.map((route) => route.path);

    expect(new Set(paths).size).toBe(paths.length);
    expect(surfaceRoutes.every((route) => route.status.length > 0)).toBe(true);
    expect(surfaceRoutes.every((route) => route.family.length > 0)).toBe(true);
    expect(surfaceRoutes.every((route) => route.mode.length > 0)).toBe(true);
    expect(surfaceRoutes.every((route) => route.navGroup.length > 0)).toBe(true);
    expect(surfaceRoutes.every((route) => route.ownerPersona.length > 0)).toBe(true);
    expect(surfaceRoutes.every((route) => route.firstScreenIntent.length > 0)).toBe(true);
  });

  it("drives generated routes and marketer navigation from one registry", () => {
    expect(generatedSurfaceRoutes.map((route) => route.path)).toContain("/service-profile");
    expect(generatedSurfaceRoutes.map((route) => route.path)).toContain("/social-publisher");
    expect(primarySurfaceRoutes.map((route) => route.path)).toEqual([
      "/command-center",
      "/opportunities",
      "/content-planner",
      "/ads-doctor",
      "/merchant",
      "/localo",
      "/actions"
    ]);
    expect(primarySurfaceRoutes.map((route) => route.label)).toEqual([
      "Dzisiaj",
      "Kolejka",
      "Treści i SEO",
      "Reklamy i pomiar",
      "Produkty",
      "Lokalnie",
      "Akcje"
    ]);
    expect(secondarySurfaceRoutes.map((route) => route.path)).toEqual([
      "/workflows",
      "/ga4",
      "/knowledge",
      "/settings"
    ]);
    expect(secondarySurfaceRoutes.map((route) => route.label)).toEqual([
      "Procesy",
      "GA4",
      "Wiedza",
      "Źródła"
    ]);

    for (const route of [...primarySurfaceRoutes, ...secondarySurfaceRoutes]) {
      expect(route.icon).toBeDefined();
    }
  });

  it("keeps placeholder, experimental and technical surfaces out of primary marketer navigation", () => {
    const primaryPaths = new Set<string>(primarySurfaceRoutes.map((route) => route.path));
    const primaryLabels = new Set<string>(primarySurfaceRoutes.map((route) => route.label));

    for (const route of surfaceRoutes) {
      if (
        route.status === "placeholder" ||
        route.status === "experimental" ||
        route.mode === "technical"
      ) {
        expect(primaryPaths.has(route.path)).toBe(false);
      }
    }
    expect(primaryLabels.has("Procesy")).toBe(false);
    expect(primaryLabels.has("Szanse")).toBe(false);
    expect(primaryLabels.has("Baza wiedzy")).toBe(false);
    expect(primaryLabels.has("Ustawienia")).toBe(false);
  });

  it("prevents App and Shell from keeping separate route arrays", () => {
    const appSource = readFileSync("src/routes/App.tsx", "utf8");
    const shellSource = readFileSync("src/components/Shell.tsx", "utf8");

    expect(appSource).toContain("generatedSurfaceRoutes");
    expect(appSource).not.toContain("const operatingRoutes =");
    expect(shellSource).toContain("primarySurfaceRoutes");
    expect(shellSource).toContain("secondarySurfaceRoutes");
    expect(shellSource).not.toContain("const primaryRoutes =");
  });
});
