import { z } from "zod";

export const ContentWorkItemSchema = z.object({
  id: z.string(),
  topic: z.string(),
  source_public_url: z.string().nullable().optional(),
  final_canonical_url: z.string().nullable().optional(),
  intended_final_url: z.string().nullable().optional(),
  preview_url: z.string().nullable().optional(),
  evidence_ids: z.array(z.string()).default([]),
  source_connectors: z.array(z.string()).default([]),
  inventory_status: z.string(),
  canonical_status: z.string(),
  duplicate_status: z.string(),
  preflight_status: z.string().default("missing"),
  preserve_first_plan_status: z.string().default("missing"),
  sales_brief_status: z.string().default("missing"),
  sales_brief_id: z.string().nullable().optional(),
  claim_ledger_status: z.string().default("missing"),
  claim_ledger_id: z.string().nullable().optional(),
  draft_package_status: z.string().default("missing"),
  draft_package_id: z.string().nullable().optional(),
  human_review_status: z.string().default("missing"),
  human_review_id: z.string().nullable().optional(),
  wordpress_handoff_status: z.string().default("missing"),
  wordpress_post_id: z.string().nullable().optional(),
  measurement_window_status: z.string().default("missing"),
  measurement_window_id: z.string().nullable().optional(),
  audit_status: z.string().default("missing"),
  audit_id: z.string().nullable().optional()
});

export const ContentWorkflowBlockerSchema = z.object({
  code: z.string(),
  label: z.string(),
  reason: z.string(),
  next_step: z.string()
});

export const ContentInventoryResolutionSchema = z.object({
  status: z.string(),
  recommended_mode: z.string(),
  matched_url: z.string().nullable().optional(),
  similar_existing_urls: z.array(z.string()).default([]),
  duplicate_risk: z.string(),
  blockers: z.array(ContentWorkflowBlockerSchema).default([]),
  evidence_ids: z.array(z.string()).default([]),
  source_connectors: z.array(z.string()).default([])
});

export const ContentPreflightVerdictSchema = z.object({
  status: z.string(),
  recommended_mode: z.string(),
  create_allowed: z.boolean(),
  sales_brief_allowed: z.boolean(),
  draft_allowed: z.boolean(),
  wordpress_draft_allowed: z.boolean(),
  final_canonical_url: z.string().nullable().optional(),
  preview_url: z.string().nullable().optional(),
  similar_existing_urls: z.array(z.string()).default([]),
  blockers: z.array(ContentWorkflowBlockerSchema).default([]),
  blocked_claims: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()).default([]),
  source_connectors: z.array(z.string()).default([]),
  next_step: z.string()
});

export const ContentWorkItemPreflightResponseSchema = z.object({
  item: ContentWorkItemSchema,
  inventory_resolution: ContentInventoryResolutionSchema,
  preflight_verdict: ContentPreflightVerdictSchema
});

export const ContentClaimReferenceSchema = z.object({
  claim_id: z.string().optional(),
  claim_text: z.string().optional(),
  claim_type: z.string().optional(),
  status: z.string().optional(),
  evidence_ids: z.array(z.string()).optional(),
  reason: z.string().optional()
});

export const ContentSalesBriefSchema = z.object({
  id: z.string(),
  work_item_id: z.string(),
  content_mode: z.string(),
  source_public_url: z.string().nullable().optional(),
  final_canonical_url: z.string(),
  intended_final_url: z.string().nullable().optional(),
  preview_url: z.string().nullable().optional(),
  target_reader: z.string(),
  buyer_problem: z.string(),
  buyer_trigger: z.string(),
  search_intent: z.string(),
  service_fit: z.string(),
  existing_content_plan: z.string(),
  outline: z.array(z.unknown()).default([]),
  allowed_claims: z.array(ContentClaimReferenceSchema).default([]),
  forbidden_claims: z.array(ContentClaimReferenceSchema).default([]),
  evidence_ids: z.array(z.string()),
  source_connectors: z.array(z.string()),
  measurement_plan: z.object({
    measurement_window_id: z.string(),
    allowed_metrics: z.array(z.string()).default([]),
    earliest_verdict_date: z.string().nullable().optional(),
    success_claim_allowed: z.boolean().default(false)
  }),
  draft_allowed: z.boolean(),
  human_review_required: z.boolean()
});

export const ContentSalesBriefBuildResultSchema = z.object({
  brief: ContentSalesBriefSchema.nullable().optional(),
  blockers: z.array(ContentWorkflowBlockerSchema).default([])
});

export const ContentWorkItemSalesBriefResponseSchema = z.object({
  item: ContentWorkItemSchema,
  inventory_resolution: ContentInventoryResolutionSchema,
  preflight_verdict: ContentPreflightVerdictSchema,
  sales_brief_result: ContentSalesBriefBuildResultSchema
});

export const ContentDraftPackageSchema = z.object({
  id: z.string(),
  work_item_id: z.string(),
  brief_id: z.string(),
  claim_ledger_id: z.string(),
  draft_kind: z.string(),
  title: z.string(),
  sections: z.array(z.unknown()).default([]),
  section_to_evidence_map: z.array(z.unknown()).default([]),
  claims_used: z.array(z.string()).default([]),
  claims_removed_or_blocked: z.array(z.string()).default([]),
  human_review_questions: z.array(z.string()).default([]),
  publish_ready: z.boolean()
});

export const ContentDraftPackageBuildResultSchema = z.object({
  draft_package: ContentDraftPackageSchema.nullable().optional(),
  blockers: z.array(ContentWorkflowBlockerSchema).default([])
});

export const ContentWorkItemDraftPackageResponseSchema = z.object({
  item: ContentWorkItemSchema,
  inventory_resolution: ContentInventoryResolutionSchema,
  preflight_verdict: ContentPreflightVerdictSchema,
  sales_brief_result: ContentSalesBriefBuildResultSchema,
  draft_package_result: ContentDraftPackageBuildResultSchema
});

export const ContentHumanReviewSchema = z.object({
  id: z.string(),
  work_item_id: z.string(),
  stage: z.string(),
  reviewed_by: z.string(),
  decision: z.string(),
  notes: z.string(),
  checked_items: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()).default([]),
  blocked_claims_handled: z.array(z.string()).default([]),
  draft_package_id: z.string().nullable().optional()
});

export const ContentWorkItemHumanReviewResponseSchema = z.object({
  item: ContentWorkItemSchema,
  reviewed_item: ContentWorkItemSchema,
  review: ContentHumanReviewSchema,
  blockers: z.array(ContentWorkflowBlockerSchema).default([]),
  wordpress_handoff_allowed: z.boolean()
});

export const ContentWordPressDraftHandoffSchema = z.object({
  id: z.string(),
  work_item_id: z.string(),
  draft_package_id: z.string(),
  human_review_id: z.string(),
  audit_id: z.string(),
  connector: z.literal("wordpress_ekologus"),
  operation_type: z.literal("create_wordpress_draft"),
  status: z.literal("prepared"),
  post_status: z.literal("draft"),
  title: z.string(),
  final_canonical_url: z.string(),
  intended_final_url: z.string().nullable().optional(),
  preview_url: z.string().nullable().optional(),
  evidence_ids: z.array(z.string()).default([]),
  publish_allowed: z.boolean(),
  destructive_update_allowed: z.boolean()
});

export const ContentWordPressDraftHandoffResultSchema = z.object({
  handoff: ContentWordPressDraftHandoffSchema.nullable().optional(),
  blockers: z.array(ContentWorkflowBlockerSchema).default([])
});

export const ContentWorkItemWordPressDraftHandoffResponseSchema = z.object({
  item: ContentWorkItemSchema,
  handoff_result: ContentWordPressDraftHandoffResultSchema
});

export const ContentDateRangeSchema = z.object({
  start: z.string(),
  end: z.string()
});

export const ContentMeasurementWindowSchema = z.object({
  id: z.string(),
  work_item_id: z.string(),
  content_url: z.string(),
  baseline_period: ContentDateRangeSchema,
  observation_period: ContentDateRangeSchema,
  earliest_verdict_date: z.string(),
  allowed_metrics: z.array(z.string()).default([]),
  source_connectors: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()).default([]),
  status: z.string(),
  handoff_id: z.string().nullable().optional(),
  success_claim_allowed: z.boolean()
});

export const ContentMeasurementWindowBuildResultSchema = z.object({
  window: ContentMeasurementWindowSchema.nullable().optional(),
  blockers: z.array(ContentWorkflowBlockerSchema).default([])
});

export const ContentWorkItemMeasurementWindowResponseSchema = z.object({
  item: ContentWorkItemSchema,
  updated_item: ContentWorkItemSchema,
  measurement_window_result: ContentMeasurementWindowBuildResultSchema,
  outcome_blockers: z.array(ContentWorkflowBlockerSchema).default([])
});

export type ContentWorkItem = z.infer<typeof ContentWorkItemSchema>;
export type ContentWorkItemPreflightResponse = z.infer<
  typeof ContentWorkItemPreflightResponseSchema
>;
export type ContentWorkItemSalesBriefResponse = z.infer<
  typeof ContentWorkItemSalesBriefResponseSchema
>;
export type ContentWorkItemDraftPackageResponse = z.infer<
  typeof ContentWorkItemDraftPackageResponseSchema
>;
export type ContentWorkItemHumanReviewResponse = z.infer<
  typeof ContentWorkItemHumanReviewResponseSchema
>;
export type ContentWorkItemWordPressDraftHandoffResponse = z.infer<
  typeof ContentWorkItemWordPressDraftHandoffResponseSchema
>;
export type ContentWorkItemMeasurementWindowResponse = z.infer<
  typeof ContentWorkItemMeasurementWindowResponseSchema
>;
