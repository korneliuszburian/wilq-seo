import { describe, expect, it } from "vitest";

import {
  ContentInventoryBindingResponseSchema,
  ContentInventoryMaterialResponseSchema
} from "./contentWorkflow";

describe("inventory material lineage", () => {
  it("preserves selection provenance while rejecting evidence claims for live material", () => {
    const live = ContentInventoryMaterialResponseSchema.safeParse({
      status: "ready",
      url: "https://www.ekologus.pl/news/",
      content_text: "Live preview",
      evidence_id: null,
      inventory_observation_evidence_id: "ev_inventory_old",
      material_observation_evidence_id: null,
      material_lineage_status: "live_material_not_evidence_bound",
      material_confidence: "review_required"
    });
    expect(live.success).toBe(true);
    if (live.success) {
      expect(live.data.inventory_observation_evidence_id).toBe("ev_inventory_old");
      expect(live.data.material_observation_evidence_id).toBeNull();
    }

    expect(ContentInventoryMaterialResponseSchema.safeParse({
      status: "ready",
      url: "https://www.ekologus.pl/news/",
      evidence_id: "ev_inventory_old",
      inventory_observation_evidence_id: "ev_inventory_old",
      material_observation_evidence_id: "ev_material_old",
      material_lineage_status: "live_material_not_evidence_bound"
    }).success).toBe(false);

    expect(ContentInventoryMaterialResponseSchema.safeParse({
      status: "ready",
      url: "https://www.ekologus.pl/news/",
      evidence_id: null,
      inventory_observation_evidence_id: "ev_inventory_old",
      material_observation_evidence_id: null,
      material_lineage_status: "live_material_not_evidence_bound",
      material_confidence: "source_bound"
    }).success).toBe(false);

    expect(ContentInventoryMaterialResponseSchema.safeParse({
      status: "ready",
      url: "https://www.ekologus.pl/news/",
      material_observation_evidence_id: "ev_material_old",
      material_lineage_status: "inventory_observation_bound"
    }).success).toBe(false);

    expect(ContentInventoryBindingResponseSchema.safeParse({
      status: "ready",
      url: "https://www.ekologus.pl/news/",
      evidence_id: "ev_inventory_old",
      inventory_observation_evidence_id: "ev_inventory_old",
      material_observation_evidence_id: null,
      material_lineage_status: "inventory_selection_only"
    }).success).toBe(true);

    expect(ContentInventoryBindingResponseSchema.safeParse({
      status: "ready",
      url: "https://www.ekologus.pl/news/",
      evidence_id: "ev_inventory_old",
      inventory_observation_evidence_id: "ev_inventory_old",
      material_observation_evidence_id: "ev_material_old",
      material_lineage_status: "inventory_selection_only"
    }).success).toBe(false);
  });
});
