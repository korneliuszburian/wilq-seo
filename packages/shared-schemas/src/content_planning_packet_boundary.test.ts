import { describe, expect, it } from "vitest";

import { ContentPlanningProposalResponseSchema } from "./contentWorkflow";

describe("planning packet action boundary", () => {
  it("retains the typed owner of a blocked planning POST", () => {
    const response = ContentPlanningProposalResponseSchema.parse({
      status: "blocked",
      work_item_id: "content_work_item_bdo",
      content_kind: "service",
      service_card_id: "ekologus_service_bdo_reporting",
      runtime: {
        status: "not_started",
        thread_id: null,
        turn_id: null,
        external_call_attempted: false
      },
      blockers: [{
        code: "research_packet_action_required",
        label: "Brakuje zatwierdzonego pakietu",
        reason: "Nie ma pakietu v2.",
        next_step: "Przygotuj pakiet v2.",
        owner: "WILQ content workflow"
      }],
      safe_next_step: "Przygotuj pakiet v2.",
      publish_ready: false
    });

    expect(response.blockers[0]?.owner).toBe("WILQ content workflow");
  });
});
