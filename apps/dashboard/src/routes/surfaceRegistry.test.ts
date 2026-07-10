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
      "/content-workflow",
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
      "/settings",
      "/system"
    ]);
    expect(secondarySurfaceRoutes.map((route) => route.label)).toEqual([
      "Procesy",
      "GA4",
      "Wiedza",
      "Źródła",
      "System"
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

  it("keeps Ads placeholder drilldowns hidden and technical", () => {
    const placeholderPaths = [
      "/ads-doctor/search-terms",
      "/ads-doctor/scaling",
      "/ads-doctor/seasonality",
      "/ads-doctor/recommendations"
    ];

    for (const path of placeholderPaths) {
      const route = surfaceRoutes.find((surface) => surface.path === path);

      expect(route).toBeDefined();
      expect(route?.status).toBe("placeholder");
      expect(route?.mode).toBe("technical");
      expect(route?.navGroup).toBe("hidden");
      expect(route?.firstScreenIntent.toLowerCase()).toContain("placeholder");
    }
  });

  it("keeps content inventory, social and export routes out of primary marketer navigation", () => {
    const contentInventory = surfaceRoutes.find((surface) => surface.path === "/content-inventory");
    const socialPublisher = surfaceRoutes.find((surface) => surface.path === "/social-publisher");
    const googleSheets = surfaceRoutes.find((surface) => surface.path === "/google-sheets");

    expect(contentInventory?.status).toBe("placeholder");
    expect(contentInventory?.mode).toBe("technical");
    expect(contentInventory?.navGroup).toBe("hidden");
    expect(socialPublisher?.status).toBe("experimental");
    expect(socialPublisher?.mode).toBe("technical");
    expect(socialPublisher?.navGroup).toBe("hidden");
    expect(googleSheets?.status).toBe("placeholder");
    expect(googleSheets?.mode).toBe("technical");
    expect(googleSheets?.navGroup).toBe("hidden");
    const primaryPaths = new Set<string>(primarySurfaceRoutes.map((route) => route.path));
    expect(primaryPaths.has("/content-inventory")).toBe(false);
    expect(primaryPaths.has("/social-publisher")).toBe(false);
    expect(primaryPaths.has("/google-sheets")).toBe(false);
  });

  it("keeps hidden placeholder metadata short instead of product-spec prose", () => {
    const parkedRoutes = surfaceRoutes.filter(
      (route) =>
        route.navGroup === "hidden"
        && route.mode === "technical"
        && (route.status === "placeholder" || route.status === "experimental")
    );

    for (const route of parkedRoutes) {
      expect(route.firstScreenIntent.length).toBeLessThanOrEqual(70);
    }
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
