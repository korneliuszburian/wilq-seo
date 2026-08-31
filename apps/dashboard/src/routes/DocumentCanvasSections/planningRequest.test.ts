import { describe, expect, it } from "vitest";

import { planningRequestFromResponse } from "./planningRequest";

const base = {
  status: "not_generated" as const,
  work_item_id: "content_work_item_article",
  planning_input_digest: "a".repeat(64),
  runtime: {
    status: "not_started" as const,
    thread_id: null,
    turn_id: null,
    event_methods: [],
    item_types: [],
    external_call_attempted: false
  },
  blockers: [],
  safe_next_step: "Przygotuj plan.",
  publish_ready: false as const
};

describe("planningRequestFromResponse", () => {
  it("builds editorial without inventing a service card", () => {
    expect(planningRequestFromResponse({
      ...base, content_kind: "editorial", service_card_id: null
    }, "wilku")).toMatchObject({
      content_kind: "editorial", service_card_id: null, requested_by: "wilku"
    });
  });

  it("keeps legacy service responses service-bound", () => {
    expect(planningRequestFromResponse({
      ...base, service_card_id: "service_card"
    }, "wilku")).toMatchObject({
      content_kind: "service", service_card_id: "service_card"
    });
  });
});
