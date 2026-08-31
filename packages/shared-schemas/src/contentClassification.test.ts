import { describe, expect, it } from "vitest";

import { ContentDecisionItemSchema } from "./content_diagnostics";
import {
  ContentWorkItemSchema,
  ContentWorkItemServiceProfileContextSchema
} from "./contentWorkflow";

describe("content classification browser contracts", () => {
  it("preserves WordPress type and content kind for diagnostics and workflow items", () => {
    const classification = {
      wordpress_content_type: "posts",
      content_kind: "editorial"
    };

    expect(
      ContentDecisionItemSchema.pick({
        wordpress_content_type: true,
        content_kind: true
      }).parse(classification)
    ).toEqual(classification);
    expect(
      ContentWorkItemSchema.pick({
        wordpress_content_type: true,
        content_kind: true
      }).parse(classification)
    ).toEqual(classification);
  });

  it("accepts the service-less editorial binding status", () => {
    expect(
      ContentWorkItemServiceProfileContextSchema.parse({
        binding_status: "not_required",
        decision_status: "ready",
        status_label: "Profil usługi nie jest wymagany",
        reason: "Artykuł bazy wiedzy nie jest kartą usługi.",
        safe_next_step: "Przejdź do planowania artykułu."
      }).binding_status
    ).toBe("not_required");
  });
});
