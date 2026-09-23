import { describe, expect, it } from "vitest";

import { ContentMaterialReviewActionResponseSchema } from "./content_material_review_action";

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
