import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import { briefSurfaceConfigs } from "./BriefWorkflowSurface";

describe("BriefWorkflowSurface config", () => {
  it("does not expose generic Focus or Safety Gate headings", () => {
    const visibleLabels = Object.values(briefSurfaceConfigs).flatMap((config) => [
      config.title,
      config.description,
      config.focusTitle,
      config.emptyMessage,
      config.safetyTitle,
      config.safetyText
    ]);

    expect(visibleLabels).not.toContain("Local Visibility Focus");
    expect(visibleLabels).not.toContain("Social Publishing Focus");
    expect(visibleLabels).not.toContain("Content Growth Focus");
    expect(visibleLabels).not.toContain("Feed/Product Focus");
    expect(visibleLabels.some((label) => /\bFocus\b/.test(label))).toBe(false);
    expect(visibleLabels.some((label) => /\bSafety Gate\b/.test(label))).toBe(false);
    expect(visibleLabels.some((label) => label.includes("/api/marketing/brief"))).toBe(false);
    expect(visibleLabels.some((label) => label.includes("MarketingBrief"))).toBe(false);
    expect(visibleLabels.some((label) => label.includes("spend"))).toBe(false);
    expect(visibleLabels.some((label) => label.includes("inventory"))).toBe(false);
  });

  it("renders API-owned brief kind labels instead of raw kind enums", () => {
    const source = readFileSync(
      "src/routes/BriefWorkflowSurface.tsx",
      "utf8"
    );

    expect(source).toContain("item.kind_label");
    expect(source).not.toContain("{item.kind} /");
    expect(source).not.toContain("{item.kind_label} / {item.priority_label}");
  });
});
