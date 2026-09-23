import { describe, expect, it } from "vitest";

import {
  ResearchPacketV2ActionBlockedSchema,
  ResearchPacketV2ActionReadySchema,
  ResearchPacketV2PreviewRecordSchema
} from "./content_research_packet_v2_action";

describe("v2 research packet action", () => {
  it("keeps exact ready identity and typed blocked authority", () => {
    const record = {
      schema_version: "wilq_research_packet_v2_preview_record_v1",
      preview_hash: "a".repeat(64),
      work_item_id: "wi_exact",
      snapshot: {
        status: "ready",
        preview_hash: "a".repeat(64),
        source_pack_hash: "b".repeat(64),
        work_item_id: "wi_exact",
        selected_facts: [{
          source_fact_id: "fact_exact",
          text: "Zatwierdzony fakt",
          source_reference: "https://eur-lex.europa.eu/eli/reg/2025/40/oj/pol",
          freshness_date: "2026-09-23",
          source_type: "legal_update",
          source_connectors: ["official_regulatory_review"],
          fact_digest: "b".repeat(64),
          evidence_ids: ["ev_exact"]
        }],
        planning_context: {
          target_reader: "Przedsiębiorca",
          buyer_problem: "Niejasny obowiązek",
          buyer_trigger: "Zmiana prawa",
          search_intent: "Sprawdzenie obowiązku"
        },
        internal_links: [],
        legal_requirements: [],
        evidence_ids: ["ev_exact"],
        generation_allowed: false,
        packet_write_allowed: false
      }
    };
    expect(ResearchPacketV2PreviewRecordSchema.parse(record).preview_hash).toBe("a".repeat(64));
    expect(() => ResearchPacketV2PreviewRecordSchema.parse({
      ...record,
      snapshot: { ...record.snapshot, preview_hash: "c".repeat(64) }
    })).toThrow();
    for (const missing of ["source_type", "source_connectors", "fact_digest"] as const) {
      const incompleteFact = Object.fromEntries(
        Object.entries(record.snapshot.selected_facts[0]).filter(([key]) => key !== missing)
      );
      expect(() => ResearchPacketV2PreviewRecordSchema.parse({
        ...record,
        snapshot: { ...record.snapshot, selected_facts: [incompleteFact] }
      })).toThrow();
    }
    expect(ResearchPacketV2ActionReadySchema.parse({
      response_type: "research_packet_v2_action",
      status: "preview_ready",
      action_id: "act_exact",
      external_write_attempted: false,
      generation_allowed: false
    }).status).toBe("preview_ready");
    expect(ResearchPacketV2ActionBlockedSchema.parse({
      response_type: "research_packet_v2_action",
      status: "blocked",
      blocker_code: "material_review_missing_or_stale",
      blocker_owner: "WILQ content workflow",
      evidence_ids: ["ev_exact"],
      safe_next_step: "Przejrzyj materiał.",
      external_write_attempted: false,
      generation_allowed: false
    }).blocker_owner).toBe("WILQ content workflow");
  });
});
