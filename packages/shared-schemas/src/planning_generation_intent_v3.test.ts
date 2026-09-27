import { describe, expect, it } from "vitest";

import {
  PlanningGenerationIntentV3DispatchOutcomeSchema,
  PlanningGenerationIntentV3ResponseSchema,
  type PlanningGenerationIntentV3Snapshot
} from "./planning_generation_intent_v3";

const hex = (character: string) => character.repeat(64);

function snapshot(): PlanningGenerationIntentV3Snapshot {
  return {
    schema_version: "wilq_planning_generation_intent_snapshot_v3",
    intent_digest: hex("a"),
    context_digest: hex("b"),
    approval_receipt_digest: hex("c"),
    approval_action_id: "act_content_research_packet_v3_exact",
    work_item_id: "wi_exact",
    packet_id: "content_research_packet_v3_aaaaaaaaaaaaaaaaaaaaaaaa",
    packet_digest: hex("e"),
    content_kind: "service",
    service_card_id: "card_operat",
    page_url: "https://www.ekologus.pl/operat-wodnoprawny/",
    canonical_path: "/operat-wodnoprawny",
    identity_digest: hex("f"),
    per_url_delivery_identity_action_id: "act_per_url_delivery_identity_exact",
    material_meaning_digest: hex("1"),
    source_pack_id: "source_pack_v3_aaaaaaaaaaaaaaaaaaaaaaaa",
    source_pack_hash: hex("2"),
    selected_fact_ids: ["fact_operat"],
    evidence_ids: ["ev_packet"],
    planning_context: {
      target_reader: "przedsiębiorca",
      buyer_problem: "obowiązek środowiskowy",
      buyer_trigger: "kontrola",
      search_intent: "operat wodnoprawny"
    },
    cta_direction: "umów konsultację",
    minimum_cta_blocks: 2,
    required_cta_patterns: [],
    internal_links: [
      {
        target_url: "https://www.ekologus.pl/",
        anchor_hint: "ekologus",
        source_connector: "wordpress_ekologus",
        evidence_ids: ["ev_link"]
      }
    ],
    regulatory_profile_id: "profile_operat",
    regulatory_profile_version: "1",
    legal_requirements: [
      {
        requirement_id: "req_operat_1",
        label: "obowiązek",
        source_fact_ids: ["fact_operat"],
        evidence_ids: ["ev_req"]
      }
    ],
    generation_performed: false,
    model_enqueued: false,
    external_write_attempted: false
  };
}

const ACTION = {
  id: "act_content_planning_generation_intent_v3_exact",
  title: "Zatwierdź lokalny zamiar planowania z pakietu v3",
  domain: "content",
  connector: "wordpress_ekologus",
  mode: "apply",
  risk: "low",
  status: "ready_to_apply",
  evidence_ids: ["ev_packet"],
  metrics: [],
  human_diagnosis: "Apply zapisuje wyłącznie lokalny receipt zamiaru.",
  recommended_reason: "Sprawdź dokładny pakiet v3.",
  validation_status: "not_validated",
  payload: {
    action_type: "content_planning_generation_intent_v3",
    local_authority_only: true
  },
  audit_events: []
};

describe("planning generation intent v3 contract", () => {
  it("accepts a preview-ready response with an exact snapshot", () => {
    const response = PlanningGenerationIntentV3ResponseSchema.parse({
      response_type: "planning_generation_intent_v3",
      status: "preview_ready",
      action_id: ACTION.id,
      action: ACTION,
      snapshot: snapshot(),
      generation_performed: false,
      model_enqueued: false,
      external_write_attempted: false
    });
    expect(response.status).toBe("preview_ready");
    if (response.status === "preview_ready") {
      expect(response.snapshot.packet_digest).toBe(hex("e"));
      expect(response.model_enqueued).toBe(false);
    }
  });

  it("accepts a blocked response with a typed blocker", () => {
    const response = PlanningGenerationIntentV3ResponseSchema.parse({
      response_type: "planning_generation_intent_v3",
      status: "blocked",
      work_item_id: "wi_exact",
      blocker_code: "research_packet_v3_approval_missing",
      blocker_owner: "WILQ content workflow",
      evidence_ids: ["ev_packet"],
      safe_next_step: "Zatwierdź dokładny pakiet v3."
    });
    expect(response.status).toBe("blocked");
  });

  it("accepts an accepted dispatch outcome with its exact intent receipt", () => {
    const outcome = PlanningGenerationIntentV3DispatchOutcomeSchema.parse({
      response_type: "planning_generation_intent_v3_dispatch",
      status: "accepted",
      action_id: ACTION.id,
      work_item_id: "wi_exact",
      intent_receipt_id: "planning_generation_intent_receipt_exact",
      planning_input_digest: hex("3"),
      proposal_status: "generating",
      blocker: null,
      safe_next_step: "Odczytaj status planu."
    });
    expect(outcome.status).toBe("accepted");
    expect(outcome.intent_receipt_id).toBe("planning_generation_intent_receipt_exact");
  });

  it("rejects an accepted dispatch outcome without an intent receipt", () => {
    expect(() =>
      PlanningGenerationIntentV3DispatchOutcomeSchema.parse({
        response_type: "planning_generation_intent_v3_dispatch",
        status: "accepted",
        action_id: ACTION.id,
        intent_receipt_id: null,
        safe_next_step: "Odczytaj status planu."
      })
    ).toThrow();
  });

  it("rejects an empty service_card_id like the Python contract", () => {
    expect(() =>
      PlanningGenerationIntentV3ResponseSchema.parse({
        response_type: "planning_generation_intent_v3",
        status: "preview_ready",
        action_id: ACTION.id,
        action: ACTION,
        snapshot: { ...snapshot(), service_card_id: "" }
      })
    ).toThrow();
  });

  it("rejects an empty per-URL identity action id like the Python contract", () => {
    expect(() =>
      PlanningGenerationIntentV3ResponseSchema.parse({
        response_type: "planning_generation_intent_v3",
        status: "preview_ready",
        action_id: ACTION.id,
        action: ACTION,
        snapshot: { ...snapshot(), per_url_delivery_identity_action_id: "" }
      })
    ).toThrow();
  });

  it("rejects snapshot fact and evidence arrays above the Python item maxima", () => {
    expect(() =>
      PlanningGenerationIntentV3ResponseSchema.parse({
        response_type: "planning_generation_intent_v3",
        status: "preview_ready",
        action_id: ACTION.id,
        action: ACTION,
        snapshot: {
          ...snapshot(),
          evidence_ids: Array.from({ length: 513 }, (_, index) => `ev_${index}`)
        }
      })
    ).toThrow();
  });

  it("rejects a blocked dispatch outcome without a typed blocker", () => {
    expect(() =>
      PlanningGenerationIntentV3DispatchOutcomeSchema.parse({
        response_type: "planning_generation_intent_v3_dispatch",
        status: "blocked",
        action_id: ACTION.id,
        blocker: null,
        safe_next_step: "Odczytaj aktualny pakiet."
      })
    ).toThrow();
  });
});
