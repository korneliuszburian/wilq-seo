import { describe, expect, it } from "vitest";

import {
  ContentMaterialReviewActionResponseSchema,
  CurrentMaterialTextResponseSchema
} from "./content_material_review_action";

describe("current material review action response", () => {
  it("distinguishes an exact local preview from a typed blocker", () => {
    const ready = ContentMaterialReviewActionResponseSchema.parse({
      response_type: "content_material_review_action_v2",
      status: "preview_ready",
      action_id: "act_content_material_review_exact",
      external_write_attempted: false,
      generation_allowed: false
    });
    expect(ready.status).toBe("preview_ready");

    const blocked = ContentMaterialReviewActionResponseSchema.parse({
      response_type: "content_material_review_action_v2",
      status: "blocked",
      blocker_code: "material_review_source_stale",
      blocker_owner: "WILQ WordPress connector",
      safe_next_step: "Odśwież odczyt.",
      external_write_attempted: false,
      generation_allowed: false
    });
    expect(blocked.status).toBe("blocked");
    expect(() => ContentMaterialReviewActionResponseSchema.parse({
      ...ready,
      external_write_attempted: true
    })).toThrow();
  });
});

describe("current material text read", () => {
  it("distinguishes exact source text from a drift blocker", () => {
    const exact = CurrentMaterialTextResponseSchema.parse({
      response_type: "current_material_text_v1",
      status: "exact",
      is_generated: false,
      action_id: "act_exact",
      preview_id: "preview_exact",
      preview_digest: "a".repeat(64),
      source_url: "https://www.ekologus.pl/a/",
      title: "Bieżąca strona",
      text: "Pełny bieżący tekst.",
      body_digest: "b".repeat(64),
      read_at: "2026-09-24T05:00:00Z",
      evidence_ids: ["ev_exact"]
    });
    expect(exact.status).toBe("exact");
    expect(CurrentMaterialTextResponseSchema.safeParse({ ...exact, text: "" }).success).toBe(false);
    const blocked = CurrentMaterialTextResponseSchema.parse({
      response_type: "current_material_text_v1",
      status: "blocked",
      is_generated: false,
      blocker_code: "material_review_text_changed",
      blocker_owner: "WILQ content workflow",
      safe_next_step: "Przygotuj nowy odczyt.",
      evidence_ids: ["ev_exact"]
    });
    expect(blocked.status).toBe("blocked");
    expect("text" in blocked).toBe(false);
  });
});
