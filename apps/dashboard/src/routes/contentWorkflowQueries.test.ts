import { describe, expect, it } from "vitest";

import {
  mergeContentWorkItemQueueCatalog
} from "./contentWorkflowQueries";
import type { ContentWorkItemQueueResponse } from "../lib/api";

function queue(ids: string[]): ContentWorkItemQueueResponse {
  return {
    candidates: ids.map((work_item_id) => ({ work_item_id }))
  } as ContentWorkItemQueueResponse;
}

describe("content workflow queue catalog", () => {
  it("keeps every catalog page when a selected lightweight response arrives", () => {
    const merged = mergeContentWorkItemQueueCatalog(
      queue(["page_bdo", "page_outsourcing", "page_news"]),
      queue(["page_outsourcing"])
    );

    expect(merged?.candidates.map((candidate) => candidate.work_item_id)).toEqual([
      "page_bdo",
      "page_outsourcing",
      "page_news"
    ]);
    expect(merged?.candidate_count).toBe(3);
  });

  it("does not lose a selected page absent from the initial catalog", () => {
    const merged = mergeContentWorkItemQueueCatalog(
      queue(["page_bdo"]),
      queue(["page_new"])
    );

    expect(merged?.candidates.map((candidate) => candidate.work_item_id)).toEqual([
      "page_bdo",
      "page_new"
    ]);
  });
});
