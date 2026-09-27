import { z } from "zod";

import { codePointBoundedString, isSortedAndUnique } from "./content_intake";

function isSorted(values: readonly string[]): boolean {
  return values.every(
    (value, index) =>
      index === 0
      || value === values[index - 1]
      || isSortedAndUnique([values[index - 1], value])
  );
}

export const ContentResearchReadFactSchema = z.strictObject({
  source_fact_id: codePointBoundedString(1, 240),
  fact_digest: z.string().regex(/^[0-9a-f]{64}$/),
  source_type: z.string().min(1),
  source_url: codePointBoundedString(1, 2048),
  language: z.literal("unknown").default("unknown"),
  freshness_date: z.string().min(1),
  scope: z.string().min(1),
  authority: z.enum(["official", "reviewed"]),
  review_status: z.literal("approved").default("approved"),
  evidence_ids: z.array(z.string()).min(1),
  source_connectors: z.array(z.string()).min(1),
  target_card_id: codePointBoundedString(1, 240),
  deterministic_origin: z.enum([
    "exact_canonical_path",
    "exact_service_card_binding"
  ])
}).refine(
  (fact) => isSortedAndUnique(fact.evidence_ids),
  {
    path: ["evidence_ids"],
    message: "Research read evidence IDs must be sorted and unique."
  }
);

export const ContentResearchReadBlockedSourceSchema = z.strictObject({
  source_fact_id: codePointBoundedString(1, 240),
  review_status: z.string().min(1),
  source_url: codePointBoundedString(1, 2048),
  evidence_ids: z.array(z.string()).default([]),
  reason_code: z.literal("source_fact_review_required").default("source_fact_review_required"),
  blocker_owner: z.string().min(1),
  safe_next_step: z.string().min(1)
});

export const ContentResearchReadBlockerSchema = z.strictObject({
  code: codePointBoundedString(1, 160),
  owner: codePointBoundedString(1, 160),
  detail: codePointBoundedString(1, 600)
});

export const ContentResearchReadClaimGateSchema = z.strictObject({
  claim: z.enum(["demand", "competitor"]),
  allowed: z.literal(false).default(false),
  code: codePointBoundedString(1, 160),
  owner: codePointBoundedString(1, 160),
  detail: codePointBoundedString(1, 600)
});

export const ContentResearchReadResponseSchema = z.strictObject({
  schema_version: z.literal("wilq_content_research_read_v1").default("wilq_content_research_read_v1"),
  queue_id: codePointBoundedString(1, 240),
  work_item_id: codePointBoundedString(0, 240).nullable().default(null),
  status: z.enum(["ready", "blocked"]),
  page_url: codePointBoundedString(0, 2048).nullable().default(null),
  canonical_path: codePointBoundedString(0, 2048).nullable().default(null),
  identity_id: codePointBoundedString(0, 240).nullable().default(null),
  facts: z.array(ContentResearchReadFactSchema).default([]),
  blocked_sources: z.array(ContentResearchReadBlockedSourceSchema).default([]),
  blockers: z.array(ContentResearchReadBlockerSchema).default([]),
  claim_gates: z.array(ContentResearchReadClaimGateSchema).default([]),
  research_packet_created: z.literal(false).default(false),
  action_created: z.literal(false).default(false),
  generation_allowed: z.literal(false).default(false),
  safe_next_step: codePointBoundedString(1, 600)
}).superRefine((item, context) => {
  if (item.status === "blocked" && (!item.blockers.length || item.facts.length)) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["status"],
      message: "Blocked research reads need a blocker and no accepted facts."
    });
  }
  if (item.status === "ready" && !item.facts.length) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["facts"],
      message: "Ready research reads need at least one accepted fact."
    });
  }
  if (new Set(item.blockers.map((blocker) => blocker.code)).size !== item.blockers.length) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["blockers"],
      message: "Research read blockers must be unique."
    });
  }
  if (new Set(item.claim_gates.map((gate) => gate.claim)).size !== item.claim_gates.length) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["claim_gates"],
      message: "Research read claim gates must be unique."
    });
  }
});

export const ContentRequestWorkflowGateSchema = z.strictObject({
  code: codePointBoundedString(1, 160),
  status: z.enum(["pending", "approved", "rejected", "stale"]),
  owner: codePointBoundedString(1, 160),
  evidence_ids: z.array(z.string()).default([]),
  safe_next_step: codePointBoundedString(1, 600)
});

export const ContentRequestWorkflowStateSchema = z.strictObject({
  schema_version: z.literal("wilq_request_workflow_state_v1").default("wilq_request_workflow_state_v1"),
  queue_id: codePointBoundedString(1, 240),
  status: z.enum(["in_progress", "blocked", "ready_for_brief", "failed"]),
  current_step: z.enum([
    "intake_accepted",
    "research_read",
    "human_review",
    "brief_ready",
    "failed"
  ]),
  gates: z.array(ContentRequestWorkflowGateSchema).default([]),
  lineage_event_ids: z.array(z.string()).default([]),
  latest_idempotency_key: codePointBoundedString(0, 240).nullable().default(null),
  event_count: z.number().int().min(0),
  evidence_ids: z.array(z.string()).default([]),
  blocker_code: codePointBoundedString(0, 160).nullable().default(null),
  blocker_owner: codePointBoundedString(0, 160).nullable().default(null),
  safe_next_step: codePointBoundedString(1, 600),
  generation_allowed: z.literal(false).default(false),
  updated_at: z.string().datetime({ offset: true })
}).superRefine((item, context) => {
  const hasTypedBlocker = Boolean(item.blocker_code && item.blocker_owner);
  if (["blocked", "failed"].includes(item.status) && !hasTypedBlocker) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["blocker_code"],
      message: "Blocked or failed request workflow needs one typed blocker."
    });
  }
  if (!["blocked", "failed"].includes(item.status) && (item.blocker_code || item.blocker_owner)) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["blocker_code"],
      message: "Only a blocked or failed request workflow carries a blocker."
    });
  }
  if (new Set(item.gates.map((gate) => gate.code)).size !== item.gates.length) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["gates"],
      message: "Request workflow gates must be unique."
    });
  }
  if (!isSorted(item.lineage_event_ids)) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["lineage_event_ids"],
      message: "Request workflow lineage must be sorted."
    });
  }
  if (!isSortedAndUnique(item.evidence_ids)) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["evidence_ids"],
      message: "Request workflow evidence IDs must be sorted and unique."
    });
  }
});

export type ContentResearchReadFact = z.infer<typeof ContentResearchReadFactSchema>;
export type ContentResearchReadBlockedSource = z.infer<typeof ContentResearchReadBlockedSourceSchema>;
export type ContentResearchReadBlocker = z.infer<typeof ContentResearchReadBlockerSchema>;
export type ContentResearchReadClaimGate = z.infer<typeof ContentResearchReadClaimGateSchema>;
export type ContentResearchReadResponse = z.infer<typeof ContentResearchReadResponseSchema>;
export type ContentRequestWorkflowGate = z.infer<typeof ContentRequestWorkflowGateSchema>;
export type ContentRequestWorkflowState = z.infer<typeof ContentRequestWorkflowStateSchema>;
