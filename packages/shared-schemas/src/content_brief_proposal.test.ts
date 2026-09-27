import { describe, expect, it } from "vitest";

import {
  ContentBriefProposalSchema,
  type ContentBriefProposal
} from "./content_brief_proposal";

const QUEUE_ID = "content_intake_c47b408cbdf7d42231f3a277";

function readyBrief(): ContentBriefProposal {
  return ContentBriefProposalSchema.parse({
    schema_version: "wilq_content_brief_proposal_v1",
    queue_id: QUEUE_ID,
    status: "ready",
    route: "existing_page",
    target_work_item_id: "wi_operat",
    target_path: "/operat-wodnoprawny",
    target_public_url: "https://ekologus.test/operat-wodnoprawny",
    fields: [
      {
        field: "zakres",
        value: "operat wodnoprawny",
        provenance: "evidence",
        detail: "Zatwierdzony fakt źródłowy.",
        evidence_ids: ["ev_fact_a", "ev_fact_b"]
      }
    ],
    blockers: [],
    workflow_step: "brief_ready",
    research_status: "ready",
    planning_proposal_created: false,
    action_created: false,
    generation_allowed: false,
    safe_next_step: "Otwórz existing-page workflow z tym briefem."
  });
}

describe("content brief proposal contract", () => {
  it("accepts a ready existing-page brief with an exact target", () => {
    const brief = readyBrief();
    expect(brief.route).toBe("existing_page");
    expect(brief.target_work_item_id).toBe("wi_operat");
  });

  it("rejects a ready brief without a route", () => {
    expect(() =>
      ContentBriefProposalSchema.parse({ ...readyBrief(), route: null })
    ).toThrow();
  });

  it("rejects a ready brief that carries blockers", () => {
    expect(() =>
      ContentBriefProposalSchema.parse({
        ...readyBrief(),
        blockers: [
          { code: "x", owner: "Wilku", detail: "y" }
        ]
      })
    ).toThrow();
  });

  it("rejects a blocked brief without a typed blocker", () => {
    expect(() =>
      ContentBriefProposalSchema.parse({
        ...readyBrief(),
        status: "blocked",
        route: "new_page",
        target_work_item_id: null,
        target_path: null,
        target_public_url: null,
        blockers: []
      })
    ).toThrow();
  });

  it("rejects an existing-page route without its exact target", () => {
    expect(() =>
      ContentBriefProposalSchema.parse({
        ...readyBrief(),
        target_work_item_id: null,
        target_path: null
      })
    ).toThrow();
  });

  it("rejects duplicate field names and duplicate blocker codes", () => {
    const field = readyBrief().fields[0];
    expect(() =>
      ContentBriefProposalSchema.parse({ ...readyBrief(), fields: [field, field] })
    ).toThrow();
    expect(() =>
      ContentBriefProposalSchema.parse({
        ...readyBrief(),
        status: "blocked",
        route: "new_page",
        target_work_item_id: null,
        target_path: null,
        target_public_url: null,
        blockers: [
          { code: "dup", owner: "Wilku", detail: "a" },
          { code: "dup", owner: "Wilku", detail: "b" }
        ]
      })
    ).toThrow();
  });

  it("accepts Python-valid empty optional targets and a defaulted schema version", () => {
    const payload: Record<string, unknown> = {
      ...readyBrief(),
      status: "blocked",
      route: "new_page",
      target_work_item_id: "",
      target_path: "",
      target_public_url: "",
      blockers: [{ code: "brief_route_missing", owner: "Wilku", detail: "Brak źródła." }]
    };
    delete payload.schema_version;
    const brief = ContentBriefProposalSchema.parse(payload);
    expect(brief.schema_version).toBe("wilq_content_brief_proposal_v1");
    expect(brief.target_path).toBe("");
  });
});
