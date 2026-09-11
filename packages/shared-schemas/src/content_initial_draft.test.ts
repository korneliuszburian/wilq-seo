import { describe, expect, it } from "vitest";

import {
  ContentInitialDraftBlockerSchema,
  ContentInitialDraftConflictResponseSchema,
  ContentInitialDraftGenerationResponseSchema,
  ContentInitialDraftRequestSchema,
  ContentInitialDraftResponseSchema,
  ContentInitialDraftReuseRequestSchema,
  ContentWorkItemInitialDraftRequestSchema,
  ContentWorkItemInitialDraftResponseSchema
} from "./content_initial_draft";

const digest = (character: string): string => character.repeat(64);

describe("content initial draft contracts", () => {
  it("keeps new-page generation narrow and existing-work submit a strict union", () => {
    const generation = {
      expected_proposal_id: "proposal_1",
      expected_planning_digest: digest("a"),
      expected_planning_input_digest: digest("b"),
      requested_by: "wilku"
    };
    const reuse = {
      expected_production_classification_run_digest: digest("c"),
      requested_by: "wilku"
    };

    expect(ContentInitialDraftRequestSchema.parse(generation)).toEqual(generation);
    expect(ContentInitialDraftRequestSchema.safeParse({
      ...generation,
      refresh_preparation_authorization_id: "content_refresh_preparation_authorization_test"
    }).success).toBe(false);
    expect(ContentInitialDraftRequestSchema.parse({
      ...generation,
      refresh_preparation_authorization_id: "content_refresh_preparation_authorization_test",
      expected_refresh_preparation_authorization_digest: digest("f")
    }).expected_refresh_preparation_authorization_digest).toBe(digest("f"));
    expect(ContentInitialDraftReuseRequestSchema.parse(reuse)).toEqual(reuse);
    expect(ContentWorkItemInitialDraftRequestSchema.parse(generation)).toEqual(generation);
    expect(ContentWorkItemInitialDraftRequestSchema.parse(reuse)).toEqual(reuse);
    expect(ContentInitialDraftRequestSchema.safeParse(reuse).success).toBe(false);
    expect(ContentWorkItemInitialDraftRequestSchema.safeParse({
      ...generation,
      ...reuse
    }).success).toBe(false);
    expect(ContentWorkItemInitialDraftRequestSchema.safeParse({
      ...reuse,
      requested_by: "   "
    }).success).toBe(false);
    expect(ContentWorkItemInitialDraftRequestSchema.safeParse({
      ...reuse,
      unexpected: true
    }).success).toBe(false);
  });

  it("preserves the generation-only response contract", () => {
    const blocked = blockedResponse();
    expect(ContentInitialDraftGenerationResponseSchema.parse(blocked).status).toBe("blocked");
    expect(ContentInitialDraftResponseSchema.parse(blocked).status).toBe("blocked");
    expect(ContentInitialDraftResponseSchema.safeParse({
      ...blocked,
      status: "created",
      blockers: []
    }).success).toBe(false);
    expect(ContentInitialDraftResponseSchema.safeParse({
      ...blocked,
      reuse_binding: validReusedResponse().reuse_binding
    }).success).toBe(false);
    const createdWithBlankRun = {
      ...blocked,
      status: "created" as const,
      run_id: "   ",
      revision: validReusedResponse().revision,
      blockers: []
    };
    expect(ContentInitialDraftGenerationResponseSchema.safeParse(createdWithBlankRun).success)
      .toBe(false);
    expect(ContentWorkItemInitialDraftResponseSchema.safeParse(createdWithBlankRun).success)
      .toBe(false);
  });

  it("defaults omitted blocker source codes to an emitted empty list", () => {
    const source = blockedResponse().blockers[0];
    const blocker = {
      code: source.code,
      label: source.label,
      reason: source.reason,
      next_step: source.next_step
    };

    expect(ContentInitialDraftBlockerSchema.parse(blocker).source_codes).toEqual([]);
  });

  it("keeps existing-work success and conflict HTTP channels disjoint", () => {
    const blocked = blockedResponse();
    const conflict = { ...blocked, status: "conflict" as const };
    const reused = validReusedResponse();

    expect(ContentWorkItemInitialDraftResponseSchema.parse(blocked)).toEqual(blocked);
    expect(ContentWorkItemInitialDraftResponseSchema.parse(reused)).toEqual(reused);
    expect(ContentWorkItemInitialDraftResponseSchema.safeParse(conflict).success).toBe(false);
    expect(ContentInitialDraftConflictResponseSchema.parse(conflict)).toEqual(conflict);
    expect(ContentInitialDraftConflictResponseSchema.safeParse(blocked).success).toBe(false);
    expect(ContentInitialDraftConflictResponseSchema.safeParse(reused).success).toBe(false);
  });

  it("accepts only one exact approved retained revision as reused", () => {
    const reused = validReusedResponse();
    const parsed = ContentInitialDraftResponseSchema.parse(reused);

    expect(parsed.status).toBe("reused");
    if (parsed.status !== "reused") throw new Error("expected reused response");
    expect(parsed.run_id).toBeNull();
    expect(parsed.reuse_binding.revision_digest).toBe(parsed.revision.content_digest);
    expect(parsed.reuse_binding.approved_review.decision).toBe("approved");
    expect(ContentInitialDraftGenerationResponseSchema.safeParse(reused).success).toBe(false);
  });

  it.each([
    ["proposal", (value: ReturnType<typeof validReusedResponse>) => ({
      ...value,
      proposal_id: "proposal_forbidden"
    })],
    ["run", (value: ReturnType<typeof validReusedResponse>) => ({
      ...value,
      run_id: "run_forbidden"
    })],
    ["blocker", (value: ReturnType<typeof validReusedResponse>) => ({
      ...value,
      blockers: blockedResponse().blockers
    })],
    ["runtime", (value: ReturnType<typeof validReusedResponse>) => ({
      ...value,
      runtime: { ...value.runtime, status: "completed" }
    })],
    ["revision", (value: ReturnType<typeof validReusedResponse>) => ({
      ...value,
      revision: { ...value.revision, revision_id: "other_revision" }
    })],
    ["review", (value: ReturnType<typeof validReusedResponse>) => ({
      ...value,
      reuse_binding: {
        ...value.reuse_binding,
        approved_review: {
          ...value.reuse_binding.approved_review,
          revision_digest: digest("f")
        }
      }
    })],
    ["approval", (value: ReturnType<typeof validReusedResponse>) => ({
      ...value,
      reuse_binding: {
        ...value.reuse_binding,
        approved_review: {
          ...value.reuse_binding.approved_review,
          decision: "needs_changes",
          notes: "Wymaga zmian."
        }
      }
    })],
    ["audit identity", (value: ReturnType<typeof validReusedResponse>) => ({
      ...value,
      reuse_binding: {
        ...value.reuse_binding,
        approved_review: {
          ...value.reuse_binding.approved_review,
          principal_id: "other_operator"
        }
      }
    })],
    ["blank review decision id", (value: ReturnType<typeof validReusedResponse>) => ({
      ...value,
      reuse_binding: {
        ...value.reuse_binding,
        approved_review: {
          ...value.reuse_binding.approved_review,
          decision_id: "   "
        }
      }
    })],
    ["blank reviewer", (value: ReturnType<typeof validReusedResponse>) => ({
      ...value,
      reuse_binding: {
        ...value.reuse_binding,
        approved_review: {
          ...value.reuse_binding.approved_review,
          reviewed_by: "   "
        }
      }
    })],
    ["blank binding identity", (value: ReturnType<typeof validReusedResponse>) => ({
      ...value,
      reuse_binding: { ...value.reuse_binding, classification_run_id: "   " }
    })],
    ["identity", (value: ReturnType<typeof validReusedResponse>) => ({
      ...value,
      reuse_binding: {
        ...value.reuse_binding,
        revision_work_item_id: value.reuse_binding.current_work_item_id
      }
    })],
    ["lookup", (value: ReturnType<typeof validReusedResponse>) => ({
      ...value,
      reuse_binding: { ...value.reuse_binding, lookup_basis: "current" }
    })],
    ["regeneration", (value: ReturnType<typeof validReusedResponse>) => ({
      ...value,
      reuse_binding: { ...value.reuse_binding, must_not_regenerate: false }
    })],
    ["extra", (value: ReturnType<typeof validReusedResponse>) => ({
      ...value,
      unexpected: true
    })]
  ])("rejects reused %s drift", (_name, mutate) => {
    expect(ContentInitialDraftResponseSchema.safeParse(mutate(validReusedResponse())).success)
      .toBe(false);
  });
});

function blockedResponse() {
  return {
    status: "blocked" as const,
    work_item_id: "content_work_item_bdo",
    proposal_id: "proposal_1",
    run_id: null,
    revision: null,
    reuse_binding: null,
    runtime: {
      status: "not_started" as const,
      run_id: null,
      thread_id: null,
      turn_id: null,
      event_methods: [],
      item_types: [],
      external_call_attempted: false
    },
    blockers: [{
      code: "planning_not_ready" as const,
      label: "Plan nie jest jeszcze gotowy",
      reason: "Brakuje aktualnej mapy sekcji.",
      next_step: "Sprawdź plan.",
      source_codes: [],
      retry_after_seconds: null
    }],
    safe_next_step: "Sprawdź plan.",
    publish_ready: false as const
  };
}

function validReusedResponse() {
  const currentWorkItemId = "content_work_item_inventory_bdo";
  const retainedWorkItemId = "content_work_item_retained_bdo";
  const revisionId = "content_revision_55";
  const revisionDigest = digest("a");
  const revision = {
    schema_version: "wilq_content_draft_revision_v1" as const,
    revision_id: revisionId,
    work_item_id: retainedWorkItemId,
    revision_number: 55,
    base_revision_id: null,
    content_digest: revisionDigest,
    draft_package_id: "draft_package_bdo",
    draft_package_digest: digest("b"),
    planning_digest: null,
    planning_input_digest: null,
    service_card_id: null,
    service_digest: null,
    inventory_digest: null,
    source_material_ids: [],
    knowledge_card_ids: [],
    source_provenance: [],
    document_kind: "refresh_existing" as const,
    final_canonical_url: "https://www.ekologus.pl/bdo/",
    new_page_document_identity: null,
    title: "BDO",
    page_assets: null,
    sections: [{
      section_id: null,
      heading: "Zakres BDO",
      body_markdown: "Zachowana treść BDO.",
      content_html: null,
      query_terms: [],
      evidence_ids: [],
      claim_ids: [],
      source_material_ids: [],
      knowledge_card_ids: []
    }],
    faq: [],
    cta_blocks: [],
    internal_links: [],
    official_source_references: [],
    claim_ledger: null,
    proposal_metadata: null,
    correction_reason: null,
    publish_ready: false as const,
    created_by: "wilku",
    created_at: "2026-08-30T10:05:00Z"
  };
  const approvedReview = {
    decision_id: "review_revision_55",
    decision_number: 1,
    work_item_id: retainedWorkItemId,
    revision_id: revisionId,
    revision_digest: revisionDigest,
    reviewed_by: "wilku",
    principal_id: "local_operator" as const,
    workspace_id: "ekologus_local_pilot" as const,
    trust_level: "local_unverified" as const,
    decision: "approved" as const,
    notes: "",
    checked_items: ["Dokładna treść"],
    evidence_ids: ["policy:wave0"],
    created_at: "2026-08-30T10:06:00Z"
  };
  return {
    status: "reused" as const,
    work_item_id: currentWorkItemId,
    proposal_id: null,
    run_id: null,
    revision,
    reuse_binding: {
      classification_run_id: "content_production_classification_test",
      classification_run_digest: digest("c"),
      decision_set_digest: digest("d"),
      requested_work_item_id: retainedWorkItemId,
      lookup_basis: "retained" as const,
      current_work_item_id: currentWorkItemId,
      retained_work_item_id: retainedWorkItemId,
      revision_work_item_id: retainedWorkItemId,
      identity_reconciliation_status: "fork" as const,
      revision_id: revisionId,
      revision_digest: revisionDigest,
      approved_review: approvedReview,
      must_not_regenerate: true as const
    },
    runtime: {
      status: "not_started" as const,
      run_id: null,
      thread_id: null,
      turn_id: null,
      event_methods: [],
      item_types: [],
      external_call_attempted: false as const
    },
    blockers: [],
    safe_next_step: "Otwórz dokładną zatwierdzoną rewizję.",
    publish_ready: false as const
  };
}
