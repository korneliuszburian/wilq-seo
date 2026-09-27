import { describe, expect, it } from "vitest";

import {
  ContentRequestWorkflowStateSchema,
  ContentResearchReadResponseSchema,
  type ContentRequestWorkflowState,
  type ContentResearchReadResponse
} from "./content_request_journey";

const QUEUE_ID = "content_intake_c47b408cbdf7d42231f3a277";

function blockedResearchRead(): ContentResearchReadResponse {
  return ContentResearchReadResponseSchema.parse({
    schema_version: "wilq_content_research_read_v1",
    queue_id: QUEUE_ID,
    work_item_id: null,
    status: "blocked",
    page_url: null,
    canonical_path: null,
    identity_id: null,
    facts: [],
    blocked_sources: [
      {
        source_fact_id: "sf_bdo",
        review_status: "pending",
        source_url: "https://example.test/bdo",
        evidence_ids: ["ev_blocked_source"],
        reason_code: "source_fact_review_required",
        blocker_owner: "Wilku",
        safe_next_step: "Zatwierdź fakt źródłowy BDO."
      }
    ],
    blockers: [
      {
        code: "research_target_missing",
        owner: "WILQ content workflow",
        detail: "Brak wybranej strony."
      }
    ],
    claim_gates: [
      {
        claim: "demand",
        allowed: false,
        code: "demand_evidence_not_fresh",
        owner: "WILQ demand evidence",
        detail: "Brak świeżych danych popytu."
      }
    ],
    research_packet_created: false,
    action_created: false,
    generation_allowed: false,
    safe_next_step: "Wskaż istniejącą stronę, aby odczytać dowody."
  });
}

function workflowState(): ContentRequestWorkflowState {
  return ContentRequestWorkflowStateSchema.parse({
    schema_version: "wilq_request_workflow_state_v1",
    queue_id: QUEUE_ID,
    status: "in_progress",
    current_step: "research_read",
    gates: [
      {
        code: "human_keeps_direction",
        status: "pending",
        owner: "Wilku",
        evidence_ids: ["ev_gate"],
        safe_next_step: "Zatwierdź kierunek KEEP."
      }
    ],
    lineage_event_ids: ["evt_1"],
    latest_idempotency_key: "idem_1",
    event_count: 1,
    evidence_ids: ["ev_workflow"],
    blocker_code: null,
    blocker_owner: null,
    safe_next_step: "Zatwierdź kierunek KEEP w bramce.",
    generation_allowed: false,
    updated_at: "2026-09-26T22:20:00Z"
  });
}

describe("content request journey contract", () => {
  it("accepts a blocked research read with a blocker and no accepted facts", () => {
    const read = blockedResearchRead();
    expect(read.status).toBe("blocked");
    expect(read.facts).toHaveLength(0);
  });

  it("rejects a blocked research read that carries accepted facts", () => {
    const payload = {
      ...blockedResearchRead(),
      facts: [
        {
          source_fact_id: "sf_bdo",
          fact_digest: "a".repeat(64),
          source_type: "official",
          source_url: "https://example.test/bdo",
          language: "unknown",
          freshness_date: "2026-09-01",
          scope: "ekologus",
          authority: "official",
          review_status: "approved",
          evidence_ids: ["ev_fact"],
          source_connectors: ["wordpress_ekologus"],
          target_card_id: "card_bdo",
          deterministic_origin: "exact_canonical_path"
        }
      ]
    };
    expect(() => ContentResearchReadResponseSchema.parse(payload)).toThrow();
  });

  it("rejects a ready research read without accepted facts", () => {
    expect(() =>
      ContentResearchReadResponseSchema.parse({ ...blockedResearchRead(), status: "ready", blockers: [] })
    ).toThrow();
  });

  it("accepts the derived workflow projection with one pending human gate", () => {
    const state = workflowState();
    expect(state.current_step).toBe("research_read");
    expect(state.gates[0]?.status).toBe("pending");
  });

  it("accepts Python-valid empty optional strings and a defaulted schema version", () => {
    const readPayload: Record<string, unknown> = {
      ...blockedResearchRead(),
      work_item_id: "",
      page_url: "",
      canonical_path: "",
      identity_id: ""
    };
    delete readPayload.schema_version;
    const read = ContentResearchReadResponseSchema.parse(readPayload);
    expect(read.schema_version).toBe("wilq_content_research_read_v1");
    expect(read.work_item_id).toBe("");

    const workflowPayload: Record<string, unknown> = {
      ...workflowState(),
      latest_idempotency_key: ""
    };
    delete workflowPayload.schema_version;
    const state = ContentRequestWorkflowStateSchema.parse(workflowPayload);
    expect(state.schema_version).toBe("wilq_request_workflow_state_v1");
    expect(state.latest_idempotency_key).toBe("");
  });
});
