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

// Python-derived from tests/content/test_research_packet.py with a fixed
// command timestamp. The identity/source-pack values and all digest fields are
// emitted by the server authority, not recomputed in this test.
const pythonDerivedExactPacket = {
  schema_version: "wilq_content_research_packet_v1",
  packet_id: "content_research_packet_2298e70616e45b3e18a2c271",
  packet_digest: "9c665a2daf8a1b095a1da0ac1cfa0a22634efaa372890a6303ffe549cc81d293",
  status: "exact_current",
  source_pack_binding_id: "content_source_pack_binding_fixed",
  source_pack_binding_digest: digest("b"),
  identity_binding_id: "content_delivery_identity_fixed",
  identity_binding_digest: digest("c"),
  current_work_item_id: "content_work_item_fixed",
  preparation_receipt_id: "content_research_packet_preparation_fixed",
  preparation_receipt_digest: digest("f"),
  classification_source_row_digest: digest("d"),
  canonical_path: "/bdo",
  public_url: "https://www.ekologus.pl/bdo/",
  final_disposition: "keep",
  content_kind: "service",
  intent: "bdo compliance reporting",
  query_cluster: ["bdo", "sprawozdawczość bdo"],
  canonical_owner: "/bdo",
  target_audience: "przedsiębiorca",
  buyer_problem: "brak pewności obowiązków",
  buyer_trigger: "zbliżający się termin",
  approved_source_fact_ids: [
    "fact_bdo",
    "fact_consulting"
  ],
  blocked_claims: [
    "gwarancja zgodności"
  ],
  evidence_ids: ["ev_bdo", "ev_shared"],
  source_fact_registry_digest: digest("e"),
  source_facts_digest: "aaa09175fb6bd0c6d513ab825e098f507bb469f61687bbf34bdf51c8fe1f8914",
  evidence_ids_digest: "0ee4685b7c591d780c5b0b724c442687934289ad5d34c72531d1b062791db66a",
  freshness: [
    {
      source_id: "fact_bdo",
      evidence_ids: ["ev_bdo", "ev_shared"],
      checked_at: "2026-09-15T12:00:00.123456Z",
      status: "fresh"
    },
    {
      source_id: "fact_consulting",
      evidence_ids: ["ev_bdo", "ev_shared"],
      checked_at: "2026-09-15T12:00:00.123456Z",
      status: "fresh"
    }
  ],
  legal_source_requirements: ["none_identified"],
  cta_destination: "/kontakt/",
  internal_links: [{
    destination_path: "/kontakt/",
    anchor_text: "Skontaktuj się",
    relation: "next_step",
    verification: "exact_verified"
  }],
  context_receipt: {
    schema_version: "wilq_content_research_packet_context_v1",
    classification_run_id: "classification_fixed",
    classification_run_digest: digest("a"),
    classification_source_row_digest: digest("d"),
    identity_binding_id: "content_delivery_identity_fixed",
    identity_binding_digest: digest("c"),
    source_fact_authority_receipt_id: null,
    source_fact_authority_receipt_digest: null,
    source_fact_authority_snapshot_digest: null,
    source_fact_authority_provenance_digest: null,
    service_card_id: null,
    service_semantic_digest: digest("1"),
    brief_semantic_digest: digest("2"),
    demand_evidence_digest: digest("3"),
    verified_links_digest: digest("4"),
    regulatory_coverage_digest: digest("5"),
    freshness_digest: digest("6"),
    cta_destination: "/kontakt/",
    evidence_ids: ["ev_bdo", "ev_shared"],
    source_pack_evidence_ids: [],
    source_fact_evidence_ids: [],
    demand_evidence_ids: [],
    measurement_evidence_ids: [],
    verified_link_evidence_ids: [],
    cta_evidence_ids: [],
    regulatory_evidence_ids: [],
    planning_evidence_ids: []
  },
  input_digest: "61ffcf51e90b772cec0f4d70ea3caa1448fcabc9a8d1fed15f20dc19ee715633",
  blocker: null,
  recorded_by: "research_packet_test",
  recorded_at: "2026-09-15T12:00:00.123456Z"
} as const;

describe("server-owned research packet bindings", () => {
  it("rejects stale inner digests even when outer identity is rehashed", async () => {
    await expect(verifyContentResearchPacketDigest(pythonDerivedExactPacket)).resolves.toBe(true);
    await expect(verifyContentResearchPacketDigest({
      ...pythonDerivedExactPacket,
      source_facts_digest: digest("0"),
      packet_digest: "b341b42405f831c9f46d62a2c35ab68cabd5817a0ff719d9e5491026268a6f6e"
    })).resolves.toBe(false);
    await expect(verifyContentResearchPacketDigest({
      ...pythonDerivedExactPacket,
      evidence_ids_digest: digest("0"),
      packet_digest: "0bdbf7f48528b829fb33da23e2043e30edc95eccf463f074744c18ce788c7aad"
    })).resolves.toBe(false);
    await expect(verifyContentResearchPacketDigest({
      ...pythonDerivedExactPacket,
      input_digest: digest("f"),
      packet_id: "content_research_packet_9729ec819c0184c15dd6d976",
      packet_digest: "2d22ba35d0d07b35a7d6718a13337bb229b1d6ed000cbbca3f9e0fb212a3e66b"
    })).resolves.toBe(false);
  });

  it("verifies the packet digest asynchronously with WebCrypto", async () => {
    const packetWithDigest = pythonDerivedExactPacket;
    const digestSpy = vi.spyOn(globalThis.crypto.subtle, "digest");

    await expect(verifyContentResearchPacketDigest(packetWithDigest)).resolves.toBe(true);
    await expect(verifyContentResearchPacketDigest({
      ...packetWithDigest,
      intent: "tampered"
    })).resolves.toBe(false);
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
