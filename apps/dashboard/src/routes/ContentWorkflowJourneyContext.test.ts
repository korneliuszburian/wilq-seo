import { describe, expect, it } from "vitest";

import { resolvedPageSectionCount } from "./ContentWorkflowJourneyContext";

describe("resolvedPageSectionCount", () => {
  it("uses the fresh preflight inventory instead of a stale queue projection", () => {
    expect(resolvedPageSectionCount(7, 1)).toBe(7);
  });

  it("falls back to the queue count only when preflight has no count", () => {
    expect(resolvedPageSectionCount(null, 4)).toBe(4);
    expect(resolvedPageSectionCount(undefined, null)).toBeNull();
  });
});
