import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import { generatedSurfaceRoutes, primarySurfaceRoutes, surfaceRoutes } from "./surfaceRegistry";

describe("surface registry", () => {
  it("keeps every surface path unique and explicitly classified", () => {
    const paths = surfaceRoutes.map((route) => route.path);

    expect(new Set(paths).size).toBe(paths.length);
    expect(surfaceRoutes.every((route) => route.status.length > 0)).toBe(true);
    expect(surfaceRoutes.every((route) => route.family.length > 0)).toBe(true);
  });

  it("drives generated routes and primary navigation from one registry", () => {
    expect(generatedSurfaceRoutes.map((route) => route.path)).toContain("/service-profile");
    expect(generatedSurfaceRoutes.map((route) => route.path)).toContain("/social-publisher");
    expect(primarySurfaceRoutes.map((route) => route.path)).toEqual([
      "/command-center",
      "/merchant",
      "/content-planner",
      "/ads-doctor",
      "/ga4",
      "/workflows",
      "/opportunities",
      "/actions",
      "/knowledge",
      "/settings"
    ]);

    for (const route of primarySurfaceRoutes) {
      expect(route.icon).toBeDefined();
    }
  });

  it("keeps placeholder and experimental surfaces out of primary navigation", () => {
    const primaryPaths = new Set<string>(primarySurfaceRoutes.map((route) => route.path));

    for (const route of surfaceRoutes) {
      if (route.status === "placeholder" || route.status === "experimental") {
        expect(primaryPaths.has(route.path)).toBe(false);
      }
    }
  });

  it("prevents App and Shell from keeping separate route arrays", () => {
    const appSource = readFileSync("src/routes/App.tsx", "utf8");
    const shellSource = readFileSync("src/components/Shell.tsx", "utf8");

    expect(appSource).toContain("generatedSurfaceRoutes");
    expect(appSource).not.toContain("const operatingRoutes =");
    expect(shellSource).toContain("primarySurfaceRoutes");
    expect(shellSource).not.toContain("const primaryRoutes =");
  });
});
