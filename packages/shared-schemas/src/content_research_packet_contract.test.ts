import { describe, expect, it, vi } from "vitest";

import {
  ContentInitialDraftRequestSchema,
  ContentResearchPacketCurrentProjectionSchema,
  ContentResearchPacketReadResultSchema,
  ContentResearchPacketSchema,
  ContentPlanningProposalRequestSchema,
  ContentPlanningProposalResponseSchema,
  verifyContentResearchPacketDigest
} from "./index";

const digest = (character: string): string => character.repeat(64);

describe("server-owned research packet bindings", () => {
  it("verifies the packet digest asynchronously with WebCrypto", async () => {
    const packet = {
      schema_version: "wilq_content_research_packet_v1",
      packet_id: "content_research_packet_33efe8c489591a1b6f7e9ad0",
      status: "blocked",
      source_pack_binding_id: "content_source_pack_current",
      source_pack_binding_digest: digest("b"),
      identity_binding_id: "content_delivery_identity_current",
      identity_binding_digest: digest("c"),
      current_work_item_id: "content_work_item_current",
      preparation_receipt_id: null,
      preparation_receipt_digest: null,
      classification_source_row_digest: "",
      canonical_path: "",
      public_url: "",
      final_disposition: "keep",
      content_kind: "service",
      intent: "",
      query_cluster: [],
      canonical_owner: "",
      target_audience: "",
      buyer_problem: "",
      buyer_trigger: "",
      approved_source_fact_ids: [],
      blocked_claims: [],
      evidence_ids: [],
      source_fact_registry_digest: "",
      source_facts_digest: "8138e5e9bb95f27b029fa5e119d99c2e9a6b7f44c8a07faada29f295b76297d3",
      evidence_ids_digest: "8138e5e9bb95f27b029fa5e119d99c2e9a6b7f44c8a07faada29f295b76297d3",
      freshness: [],
      legal_source_requirements: [],
      cta_destination: "",
      internal_links: [],
      context_receipt: null,
      input_digest: digest("1"),
      blocker: {
        seam: "preparation_receipt",
        reason: "preparation_receipt_missing",
        evidence_ids: [],
        next_step_pl: "Przygotuj dokładny receipt — Łódź."
      },
      recorded_by: "packet_test",
      recorded_at: "2026-09-15T00:00:00.123456Z"
    } as const;
    const packetWithDigest = {
      ...packet,
      packet_digest: "b7c264fcb77a5bc6d253bdc83c54959648c958b195900e2e87382b0dd9b9b860"
    };
    const digestSpy = vi.spyOn(globalThis.crypto.subtle, "digest");

    await expect(verifyContentResearchPacketDigest(packetWithDigest)).resolves.toBe(true);
    await expect(verifyContentResearchPacketDigest({ ...packetWithDigest, intent: "tampered" })).resolves.toBe(false);
    await expect(verifyContentResearchPacketDigest({
      ...packetWithDigest,
      packet_id: "content_research_packet_tampered"
    })).resolves.toBe(false);
    expect(digestSpy).toHaveBeenCalledWith("SHA-256", expect.any(Uint8Array));
    digestSpy.mockRestore();
  });

  it("parses strict immutable and current packet projections", () => {
    const packet = {
      schema_version: "wilq_content_research_packet_v1",
      packet_id: "content_research_packet_current",
      packet_digest: digest("a"),
      status: "exact_current",
      source_pack_binding_id: "content_source_pack_current",
      source_pack_binding_digest: digest("b"),
      identity_binding_id: "content_delivery_identity_current",
      identity_binding_digest: digest("c"),
      current_work_item_id: "content_work_item_current",
      preparation_receipt_id: "content_research_packet_preparation_current",
      preparation_receipt_digest: digest("2"),
      classification_source_row_digest: digest("d"),
      canonical_path: "/bdo/",
      public_url: "https://www.ekologus.pl/bdo/",
      final_disposition: "keep",
      content_kind: "service",
      intent: "bdo dla firm",
      query_cluster: ["bdo dla firm"],
      canonical_owner: "/bdo/",
      target_audience: "Przedsiębiorca",
      buyer_problem: "Brak pewności obowiązków.",
      buyer_trigger: "Termin sprawozdania.",
      approved_source_fact_ids: ["ekologus_public_bdo_faq_2026_07_01"],
      blocked_claims: [],
      evidence_ids: ["ev_source_pack"],
      source_fact_registry_digest: digest("e"),
      source_facts_digest: digest("f"),
      evidence_ids_digest: digest("0"),
      freshness: [{
        source_id: "ekologus_public_bdo_faq_2026_07_01",
        evidence_ids: ["ev_source_pack"],
        checked_at: "2026-09-15T00:00:00Z",
        status: "fresh"
      }],
      legal_source_requirements: ["none_identified"],
      cta_destination: "/kontakt/",
      internal_links: [{
        destination_path: "/kontakt/",
        anchor_text: "Kontakt",
        relation: "next_step",
        verification: "exact_verified"
      }],
      context_receipt: null,
      input_digest: digest("1"),
      blocker: null,
      recorded_by: "packet_test",
      recorded_at: "2026-09-15T00:00:00Z"
    };
    const current = {
      status: "current",
      packet_id: packet.packet_id,
      packet_digest: packet.packet_digest,
      current_work_item_id: packet.current_work_item_id,
      current_source_pack_binding_id: packet.source_pack_binding_id,
      current_source_pack_binding_digest: packet.source_pack_binding_digest,
      current_identity_binding_id: packet.identity_binding_id,
      current_identity_binding_digest: packet.identity_binding_digest,
      blocker: null,
      revalidated_at: "2026-09-15T00:00:00Z"
    };

    expect(ContentResearchPacketSchema.safeParse(packet).success).toBe(true);
    expect(ContentResearchPacketCurrentProjectionSchema.safeParse(current).success).toBe(true);
    expect(ContentResearchPacketReadResultSchema.safeParse({
      status: "found",
      packet,
      current
    }).success).toBe(true);
    expect(ContentResearchPacketSchema.safeParse({...packet, unexpected: true}).success).toBe(false);
    expect(ContentResearchPacketSchema.safeParse({...packet, intent: ""}).success).toBe(false);
    expect(ContentResearchPacketSchema.safeParse({...packet, final_disposition: "noindex"}).success).toBe(false);
    expect(ContentResearchPacketReadResultSchema.safeParse({
      status: "found",
      packet,
      current: {...current, packet_digest: digest("z")}
    }).success).toBe(false);
  });

  it("round-trips exact packet identity through planning and initial-draft requests", () => {
    const packet = {
      research_packet_id: "content_research_packet_current",
      research_packet_digest: digest("a")
    };
    const planning = ContentPlanningProposalRequestSchema.parse({
      content_kind: "editorial",
      service_card_id: null,
      expected_planning_input_digest: digest("b"),
      requested_by: "wilku",
      research_packet_id: packet.research_packet_id,
      expected_research_packet_digest: packet.research_packet_digest
    });
    const draft = ContentInitialDraftRequestSchema.parse({
      expected_proposal_id: "content_planning_proposal_current",
      expected_planning_digest: digest("c"),
      expected_planning_input_digest: digest("b"),
      requested_by: "wilku",
      ...packet
    });

    expect(planning.research_packet_id).toBe(packet.research_packet_id);
    expect(planning.expected_research_packet_digest).toBe(packet.research_packet_digest);
    expect(draft.research_packet_id).toBe(packet.research_packet_id);
    expect(draft.research_packet_digest).toBe(packet.research_packet_digest);
  });

  it("keeps packet identity on typed planning responses and rejects half-bindings", () => {
    const packet = {
      research_packet_id: "content_research_packet_current",
      research_packet_digest: digest("d")
    };
    const response = ContentPlanningProposalResponseSchema.parse({
      status: "blocked",
      work_item_id: "content_work_item_current",
      content_kind: "editorial",
      service_card_id: null,
      planning_input_digest: null,
      input_summary: null,
      retry_after_seconds: null,
      proposal: null,
      planning_workspace: null,
      refresh_preparation_binding: null,
      runtime: {
        status: "not_started",
        run_id: null,
        thread_id: null,
        turn_id: null,
        event_methods: [],
        item_types: [],
        external_call_attempted: false
      },
      blockers: [{
        code: "research_packet_blocked",
        label: "Packet wymaga sprawdzenia",
        reason: "Brakuje aktualnego packetu.",
        next_step: "Odśwież packet.",
        source_codes: []
      }],
      safe_next_step: "Odśwież packet.",
      publish_ready: false,
      ...packet
    });

    expect(response.research_packet_id).toBe(packet.research_packet_id);
    expect(response.research_packet_digest).toBe(packet.research_packet_digest);
    expect(ContentPlanningProposalRequestSchema.safeParse({
      content_kind: "editorial",
      service_card_id: null,
      expected_planning_input_digest: digest("b"),
      requested_by: "wilku",
      research_packet_id: packet.research_packet_id
    }).success).toBe(false);
    expect(ContentInitialDraftRequestSchema.safeParse({
      expected_proposal_id: "content_planning_proposal_current",
      expected_planning_digest: digest("c"),
      expected_planning_input_digest: digest("b"),
      requested_by: "wilku",
      research_packet_digest: packet.research_packet_digest
    }).success).toBe(false);
  });
});
