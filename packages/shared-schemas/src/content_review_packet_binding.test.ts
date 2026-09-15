import { describe, expect, it } from "vitest";

import {
  ContentSemanticReviewResponseSchema,
  ContentSemanticReviewSchema
} from "./contentWorkflow";

const dimensions = [
  "answer_directness",
  "completeness",
  "logical_flow",
  "specificity",
  "repetition",
  "search_intent_fit",
  "buyer_fit",
  "credibility",
  "conversion_clarity"
] as const;

function unboundReview() {
  return ContentSemanticReviewSchema.parse({
    review_id: "semantic_unbound",
    work_item_id: "work_packet_review",
    revision_id: "revision_packet_review",
    revision_digest: "a".repeat(64),
    criteria_version: "wilq_semantic_content_review_v1",
    codex_run_id: "codex_semantic_unbound",
    status: "reviewable",
    dimensions: dimensions.map((dimension) => ({
      dimension,
      status: "strong",
      reason: "OK",
      affected_targets: ["whole_document"]
    })),
    findings: [],
    evidence_ids: [],
    source_connectors: [],
    requested_by: "wilku",
    created_at: "2026-09-15T00:00:00Z",
    safe_next_step: "Przejdź do review.",
    publish_ready: false,
    human_review_required: true,
    action_object_created: false
  });
}

describe("packet-bound semantic review responses", () => {
  it("rejects a packet wrapper around an unbound review", () => {
    const review = unboundReview();
    const result = ContentSemanticReviewResponseSchema.safeParse({
      status: "ready",
      work_item_id: review.work_item_id,
      revision_id: review.revision_id,
      revision_digest: review.revision_digest,
      research_packet_id: "content_research_packet_current",
      research_packet_digest: "d".repeat(64),
      review,
      run_id: review.codex_run_id,
      runtime: { status: "not_started" },
      blockers: [],
      safe_next_step: review.safe_next_step,
      publish_ready: false,
      human_review_required: true,
      action_object_created: false
    });

    expect(result.success).toBe(false);
  });
});
