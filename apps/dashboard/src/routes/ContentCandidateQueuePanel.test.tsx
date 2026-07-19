import { describe, expect, it } from "vitest";

import type { ContentWorkItemQueueCandidate } from "../lib/api";
import { matchesContentQueueCandidate } from "./ContentCandidateQueuePanel";

const candidate = {
  title: "Istniejąca strona BDO",
  topic: "bdo co to",
  reason: "Niski CTR na stronie BDO.",
  source_public_url: "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/",
  final_canonical_url: "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/"
} as unknown as ContentWorkItemQueueCandidate;

describe("matchesContentQueueCandidate", () => {
  it("finds pages by title, query, and canonical URL without shrinking the API queue", () => {
    expect(matchesContentQueueCandidate(candidate, "BDO")).toBe(true);
    expect(matchesContentQueueCandidate(candidate, "bdo co to")).toBe(true);
    expect(matchesContentQueueCandidate(candidate, "/bdo-co-musi-wiedziec")).toBe(true);
    expect(matchesContentQueueCandidate(candidate, "outsourcing")).toBe(false);
    expect(matchesContentQueueCandidate(candidate, "")).toBe(true);
  });
});
