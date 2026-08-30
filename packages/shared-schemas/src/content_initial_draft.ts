import { z } from "zod";

import {
  ContentCodexRuntimeTraceSchema,
  ContentDraftRevisionReviewSchema,
  ContentDraftRevisionSchema
} from "./contentWorkflow";

const Hex64Schema = z.string().regex(/^[0-9a-f]{64}$/);
const NonBlankStringSchema = z.string().trim().min(1);
const StrictContentDraftRevisionSchema = ContentDraftRevisionSchema.strict();
const StrictContentCodexRuntimeTraceSchema = ContentCodexRuntimeTraceSchema.strict();

const ContentInitialDraftApprovedReviewSchema = ContentDraftRevisionReviewSchema.safeExtend({
  decision_id: NonBlankStringSchema,
  reviewed_by: NonBlankStringSchema,
  decision: z.literal("approved"),
  principal_id: z.literal("local_operator"),
  workspace_id: z.literal("ekologus_local_pilot"),
  trust_level: z.literal("local_unverified")
}).strict();

export const ContentInitialDraftRequestSchema = z.strictObject({
  expected_proposal_id: NonBlankStringSchema,
  expected_planning_digest: Hex64Schema,
  expected_planning_input_digest: Hex64Schema,
  requested_by: NonBlankStringSchema,
  refresh_preparation_authorization_id: NonBlankStringSchema.nullable().optional(),
  expected_refresh_preparation_authorization_digest: Hex64Schema.nullable().optional()
}).superRefine((request, context) => {
  const hasAuthorizationId = request.refresh_preparation_authorization_id != null;
  const hasAuthorizationDigest = request.expected_refresh_preparation_authorization_digest != null;
  if (hasAuthorizationId !== hasAuthorizationDigest) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      message: "Refresh preparation authorization ID and digest must be supplied together."
    });
  }
});

export const ContentInitialDraftReuseRequestSchema = z.strictObject({
  expected_production_classification_run_digest: Hex64Schema,
  requested_by: NonBlankStringSchema
});

export const ContentWorkItemInitialDraftRequestSchema = z.union([
  ContentInitialDraftRequestSchema,
  ContentInitialDraftReuseRequestSchema
]);

export const ContentInitialDraftBlockerCodeSchema = z.enum([
  "unknown_service_card",
  "service_selection_not_confirmed",
  "service_card_not_approved",
  "missing_approved_service_fact",
  "service_context_mismatch",
  "missing_planning_foundation",
  "missing_wordpress_section_inventory",
  "missing_wordpress_full_inventory",
  "wordpress_material_review_required",
  "stale_planning_sources",
  "blocked_planning_sources",
  "new_page_foundation_stale",
  "missing_new_page_service_fact",
  "missing_regulatory_source_coverage",
  "planning_not_ready",
  "draft_not_started",
  "planning_not_generated",
  "stale_planning_input",
  "proposal_mismatch",
  "revision_already_exists",
  "missing_generation_contract",
  "regulatory_preflight_failed",
  "runtime_blocked",
  "runtime_failed",
  "invalid_structured_output",
  "document_scope_mismatch",
  "generated_claim_blocked",
  "draft_assurance_failed",
  "draft_assurance_runtime_failed",
  "draft_assurance_invalid_output",
  "readability_gate_failed",
  "readability_repair_failed",
  "revision_conflict",
  "persistence_failed",
  "generation_in_progress",
  "initial_draft_queue_full",
  "stale_initial_draft_context",
  "production_classification_missing",
  "production_classification_item_missing",
  "production_classification_digest_required",
  "stale_production_classification",
  "production_generation_disabled",
  "refresh_preparation_alias_not_current",
  "refresh_preparation_decision_not_refresh",
  "refresh_preparation_service_required",
  "refresh_preparation_service_unavailable",
  "refresh_preparation_service_not_approved",
  "refresh_preparation_service_sources_missing",
  "refresh_preparation_input_blocked",
  "refresh_preparation_authorization_missing",
  "refresh_preparation_authorization_foreign",
  "refresh_preparation_authorization_digest_mismatch",
  "refresh_preparation_authorization_service_mismatch",
  "refresh_preparation_authorization_input_mismatch",
  "refresh_preparation_authorization_stale",
  "refresh_preparation_proposal_binding_mismatch",
  "refresh_preparation_acknowledgement_mismatch",
  "refresh_preparation_authorization_conflict",
  "missing_revision_owner",
  "latest_revision_missing",
  "latest_revision_drift",
  "latest_review_missing",
  "latest_review_not_approved",
  "latest_review_mismatch"
]);

export const ContentInitialDraftBlockerSchema = z.strictObject({
  code: ContentInitialDraftBlockerCodeSchema,
  label: NonBlankStringSchema,
  reason: NonBlankStringSchema,
  next_step: NonBlankStringSchema,
  source_codes: z.array(z.string()).default([]),
  retry_after_seconds: z.number().int().positive().nullable().optional()
});

export const ContentInitialDraftReuseBindingSchema = z.strictObject({
  classification_run_id: NonBlankStringSchema,
  classification_run_digest: Hex64Schema,
  decision_set_digest: Hex64Schema,
  requested_work_item_id: NonBlankStringSchema,
  lookup_basis: z.enum(["current", "retained", "historical_action_owner"]),
  current_work_item_id: NonBlankStringSchema,
  retained_work_item_id: NonBlankStringSchema.nullable(),
  revision_work_item_id: NonBlankStringSchema,
  identity_reconciliation_status: z.enum(["fork", "retained_missing"]),
  revision_id: NonBlankStringSchema,
  revision_digest: Hex64Schema,
  approved_review: ContentInitialDraftApprovedReviewSchema,
  must_not_regenerate: z.literal(true)
}).superRefine((binding, context) => {
  const forkIsExact =
    binding.retained_work_item_id !== null &&
    binding.retained_work_item_id !== binding.current_work_item_id &&
    binding.revision_work_item_id === binding.retained_work_item_id;
  const retainedMissingIsExact =
    binding.retained_work_item_id === null &&
    binding.revision_work_item_id !== binding.current_work_item_id;
  if (
    (binding.identity_reconciliation_status === "fork" && !forkIsExact) ||
    (binding.identity_reconciliation_status === "retained_missing" && !retainedMissingIsExact)
  ) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      message: "reuse identity reconciliation must name the exact revision owner"
    });
  }
  const requestedIdentity = {
    current: binding.current_work_item_id,
    retained: binding.retained_work_item_id,
    historical_action_owner: binding.revision_work_item_id
  }[binding.lookup_basis];
  if (
    requestedIdentity === null ||
    requestedIdentity !== binding.requested_work_item_id ||
    (binding.lookup_basis === "historical_action_owner" &&
      binding.identity_reconciliation_status !== "retained_missing")
  ) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      message: "reuse lookup basis must match the requested accepted identity"
    });
  }
  const review = binding.approved_review;
  if (
    review.work_item_id !== binding.revision_work_item_id ||
    review.revision_id !== binding.revision_id ||
    review.revision_digest !== binding.revision_digest
  ) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      message: "reuse review must approve the exact bound revision"
    });
  }
});

const ContentInitialDraftBaseShape = {
  work_item_id: NonBlankStringSchema,
  proposal_id: z.string().nullable(),
  run_id: z.string().nullable(),
  revision: StrictContentDraftRevisionSchema.nullable(),
  reuse_binding: ContentInitialDraftReuseBindingSchema.nullable(),
  runtime: StrictContentCodexRuntimeTraceSchema,
  blockers: z.array(ContentInitialDraftBlockerSchema),
  safe_next_step: NonBlankStringSchema,
  publish_ready: z.literal(false)
};

const ContentInitialDraftCreatedResponseSchema = z.strictObject({
  ...ContentInitialDraftBaseShape,
  status: z.literal("created"),
  run_id: NonBlankStringSchema,
  revision: StrictContentDraftRevisionSchema,
  reuse_binding: z.null(),
  blockers: z.array(ContentInitialDraftBlockerSchema).length(0)
});

const ContentInitialDraftGeneratingResponseSchema = z.strictObject({
  ...ContentInitialDraftBaseShape,
  status: z.literal("generating"),
  revision: z.null(),
  reuse_binding: z.null(),
  blockers: z.array(ContentInitialDraftBlockerSchema).min(1)
});

const ContentInitialDraftBlockedResponseSchema = z.strictObject({
  ...ContentInitialDraftBaseShape,
  status: z.literal("blocked"),
  revision: z.null(),
  reuse_binding: z.null(),
  blockers: z.array(ContentInitialDraftBlockerSchema).min(1)
});

const ContentInitialDraftFailedResponseSchema = z.strictObject({
  ...ContentInitialDraftBaseShape,
  status: z.literal("failed"),
  revision: z.null(),
  reuse_binding: z.null(),
  blockers: z.array(ContentInitialDraftBlockerSchema).min(1)
});

export const ContentInitialDraftConflictResponseSchema = z.strictObject({
  ...ContentInitialDraftBaseShape,
  status: z.literal("conflict"),
  revision: z.null(),
  reuse_binding: z.null(),
  blockers: z.array(ContentInitialDraftBlockerSchema).min(1)
});

const ContentInitialDraftReusedRuntimeSchema = z.strictObject({
  status: z.literal("not_started"),
  run_id: z.null(),
  thread_id: z.null(),
  turn_id: z.null(),
  event_methods: z.array(z.string()).length(0),
  item_types: z.array(z.string()).length(0),
  external_call_attempted: z.literal(false)
});

const ContentInitialDraftReusedResponseSchema = z.strictObject({
  ...ContentInitialDraftBaseShape,
  status: z.literal("reused"),
  proposal_id: z.null(),
  run_id: z.null(),
  revision: StrictContentDraftRevisionSchema,
  reuse_binding: ContentInitialDraftReuseBindingSchema,
  runtime: ContentInitialDraftReusedRuntimeSchema,
  blockers: z.array(ContentInitialDraftBlockerSchema).length(0)
}).superRefine((response, context) => {
  const binding = response.reuse_binding;
  if (
    response.work_item_id !== binding.current_work_item_id ||
    response.revision.work_item_id !== binding.revision_work_item_id ||
    response.revision.revision_id !== binding.revision_id ||
    response.revision.content_digest !== binding.revision_digest
  ) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      message: "reused response must expose the exact bound retained revision"
    });
  }
});

export const ContentInitialDraftGenerationResponseSchema = z.discriminatedUnion("status", [
  ContentInitialDraftCreatedResponseSchema,
  ContentInitialDraftGeneratingResponseSchema,
  ContentInitialDraftBlockedResponseSchema,
  ContentInitialDraftFailedResponseSchema,
  ContentInitialDraftConflictResponseSchema
]);

export const ContentWorkItemInitialDraftResponseSchema = z.discriminatedUnion("status", [
  ContentInitialDraftCreatedResponseSchema,
  ContentInitialDraftGeneratingResponseSchema,
  ContentInitialDraftReusedResponseSchema,
  ContentInitialDraftBlockedResponseSchema,
  ContentInitialDraftFailedResponseSchema
]);

export const ContentInitialDraftResponseSchema = z.discriminatedUnion("status", [
  ContentInitialDraftCreatedResponseSchema,
  ContentInitialDraftGeneratingResponseSchema,
  ContentInitialDraftReusedResponseSchema,
  ContentInitialDraftBlockedResponseSchema,
  ContentInitialDraftFailedResponseSchema,
  ContentInitialDraftConflictResponseSchema
]);

export type ContentInitialDraftRequest = z.infer<typeof ContentInitialDraftRequestSchema>;
export type ContentInitialDraftReuseRequest = z.infer<
  typeof ContentInitialDraftReuseRequestSchema
>;
export type ContentWorkItemInitialDraftRequest = z.infer<
  typeof ContentWorkItemInitialDraftRequestSchema
>;
export type ContentInitialDraftReuseBinding = z.infer<
  typeof ContentInitialDraftReuseBindingSchema
>;
export type ContentInitialDraftGenerationResponse = z.infer<
  typeof ContentInitialDraftGenerationResponseSchema
>;
export type ContentInitialDraftConflictResponse = z.infer<
  typeof ContentInitialDraftConflictResponseSchema
>;
export type ContentWorkItemInitialDraftResponse = z.infer<
  typeof ContentWorkItemInitialDraftResponseSchema
>;
export type ContentInitialDraftResponse = z.infer<typeof ContentInitialDraftResponseSchema>;
