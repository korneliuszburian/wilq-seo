import { describe, expect, it } from "vitest";

import type {
  ContentInventoryCatalogResponse,
  ContentWorkItemQueueCandidate
} from "../lib/api";
import {
  candidateEvidenceSummary,
  contentQueueVisibleCandidates,
  matchesContentQueueCandidate
} from "./ContentCandidateQueuePanel";

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
    expect(
      matchesContentQueueCandidate(
        {
          ...candidate,
          page_inventory: {
            content_summary: "Informacje o obowiązkach przedsiębiorcy",
            section_headings: ["Jak zalogować się do systemu BDO"],
            acf_section_headings: ["Kogo dotyczy obowiązek BDO"]
          }
        } as unknown as ContentWorkItemQueueCandidate,
        "kogo dotyczy obowiązek"
      )
    ).toBe(true);
    expect(
      matchesContentQueueCandidate(
        {
          ...candidate,
          page_inventory: { section_headings: ["Jak zalogować się do systemu BDO"] }
        } as unknown as ContentWorkItemQueueCandidate,
        "zalogować się do systemu"
      )
    ).toBe(true);
    expect(matchesContentQueueCandidate(candidate, "outsourcing")).toBe(false);
    expect(matchesContentQueueCandidate(candidate, "")).toBe(true);
  });
});

describe("candidateEvidenceSummary", () => {
  it("shows the decision meat without inventing missing metrics", () => {
    const withMetrics = {
      ...candidate,
      search_metrics: {
        impressions: 266,
        clicks: 1,
        ctr: 0.003759398,
        best_average_position: 12.5521,
        query_count: 7,
        comparison_status: "not_available",
        primary_query: "bdo co to"
      },
      page_inventory: {
        section_count: 12,
        content_inventory_status: "available"
      }
    } as unknown as ContentWorkItemQueueCandidate;
    expect(candidateEvidenceSummary(withMetrics)).toContain("266 wyśw.");
    expect(candidateEvidenceSummary(withMetrics)).toContain("CTR 0,38%");
    expect(candidateEvidenceSummary(withMetrics)).toContain("poz. 12,6");
    expect(candidateEvidenceSummary(withMetrics)).toContain("7 zapytań");
    expect(candidateEvidenceSummary(withMetrics)).toContain("brak porównywalnego okresu");
    expect(candidateEvidenceSummary(withMetrics)).toContain("12 sekcji");
    expect(candidateEvidenceSummary(candidate)).toBe("Brak exact metryk lub materiału do wyboru.");
  });

  it("prefers the current full-inventory section count over a stale queue projection", () => {
    const withStaleQueueProjection = {
      ...candidate,
      work_item_id: "work-item-bdo",
      search_metrics: { impressions: 181, clicks: 0, ctr: 0, query_count: 13 },
      page_inventory: { section_count: 1, content_inventory_status: "available" }
    } as unknown as ContentWorkItemQueueCandidate;
    expect(
      candidateEvidenceSummary(withStaleQueueProjection, {
        items: [
          {
            work_item_id: "work-item-bdo",
            url: "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/",
            section_count: 12,
            material_status: "content_and_structure"
          }
        ]
      } as unknown as ContentInventoryCatalogResponse)
    ).toContain("12 nagłówków inventory WordPress");
    expect(
      candidateEvidenceSummary(withStaleQueueProjection, {
        items: [
          {
            work_item_id: "work-item-other",
            url: "https://www.ekologus.pl/inna-strona/",
            section_count: 12,
            material_status: "content_and_structure"
          }
        ]
      } as unknown as ContentInventoryCatalogResponse)
    ).toContain("1 sekcji z projekcji kolejki");
  });
});

describe("contentQueueVisibleCandidates", () => {
  it("keeps the first view bounded while preserving an explicit full queue", () => {
    const candidates = Array.from({ length: 13 }, (_, index) => ({
      ...candidate,
      work_item_id: `candidate-${index}`
    })) as unknown as ContentWorkItemQueueCandidate[];

    expect(contentQueueVisibleCandidates(candidates, false)).toHaveLength(12);
    expect(contentQueueVisibleCandidates(candidates, false).at(-1)?.work_item_id).toBe(
      "candidate-11"
    );
    expect(contentQueueVisibleCandidates(candidates, true)).toHaveLength(13);
  });
});
