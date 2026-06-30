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
  next_step: z.string(),
  blocks_current_stage: z.boolean().optional()
});

export const ContentInventoryRecordSchema = z.object({
  id: z.string(),
  url: z.string(),
  final_canonical_url: z.string().nullable().optional(),
  intended_final_url: z.string().nullable().optional(),
  preview_url: z.string().nullable().optional(),
  content_status: z.string(),
  source_connectors: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()).default([]),
  title: z.string().nullable().optional(),
  h1: z.string().nullable().optional(),
  topic_tags: z.array(z.string()).default([])
});

export const ContentInventoryResolutionSchema = z.object({
  status: z.string(),
  recommended_mode: z.string(),
  records: z.array(ContentInventoryRecordSchema).default([]),
  similar_existing_urls: z.array(z.string()).default([]),
  blockers: z.array(ContentWorkflowBlockerSchema).default([]),
  evidence_ids: z.array(z.string()).default([]),
  source_connectors: z.array(z.string()).default([]),
  next_step: z.string()
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
  id: z.string().optional(),
  claim_text: z.string().optional(),
  claim_type: z.string().optional(),
  status: z.string().optional(),
  evidence_ids: z.array(z.string()).optional(),
  reason: z.string().optional()
});

export const ContentSalesBriefSourceFactSchema = z.object({
  evidence_id: z.string(),
  source_connector: z.string(),
  summary: z.string()
});

export const ContentSalesBriefSchema = z.object({
  id: z.string(),
  work_item_id: z.string(),
  topic: z.string(),
  target_reader: z.string(),
  buyer_problem: z.string(),
  buyer_trigger: z.string(),
  search_intent: z.string(),
  service_fit: z.string(),
  source_public_url: z.string().nullable().optional(),
  final_canonical_url: z.string(),
  intended_final_url: z.string().nullable().optional(),
  preview_url: z.string().nullable().optional(),
  existing_content_plan: z.string(),
  h1_direction: z.string(),
  h2_direction: z.array(z.string()).default([]),
  faq_direction: z.array(z.string()).default([]),
  cta_direction: z.string(),
  internal_link_direction: z.array(z.string()).default([]),
  source_facts: z.array(ContentSalesBriefSourceFactSchema).default([]),
  forbidden_claims: z.array(ContentClaimReferenceSchema).default([]),
  missing_evidence: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()),
  source_connectors: z.array(z.string()),
  measurement_plan: z.object({
    measurement_window_id: z.string(),
    metrics_to_watch: z.array(z.string()).default([]),
    earliest_verdict_note: z.string(),
    success_claim_rule: z.string()
  }),
  human_review_required: z.boolean(),
  draft_allowed: z.boolean()
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

export const StructuredDraftSourceFactSchema = z.object({
  evidence_id: z.string(),
  source_connector: z.string(),
  summary: z.string()
});

export const StructuredDraftSectionInputSchema = z.object({
  heading: z.string(),
  purpose: z.string(),
  evidence_ids: z.array(z.string()).default([]),
  draft_notes: z.array(z.string()).default([])
});

export const StructuredDraftGenerationInputSchema = z.object({
  work_item_id: z.string(),
  language: z.literal("pl-PL"),
  draft_kind: z.enum(["section_draft", "full_draft"]),
  title: z.string(),
  final_canonical_url: z.string(),
  source_public_url: z.string().nullable().optional(),
  preview_url: z.string().nullable().optional(),
  target_reader: z.string(),
  buyer_problem: z.string(),
  buyer_trigger: z.string(),
  search_intent: z.string(),
  service_fit: z.string(),
  cta_direction: z.string(),
  sections: z.array(StructuredDraftSectionInputSchema).default([]),
  source_facts: z.array(StructuredDraftSourceFactSchema).default([]),
  claims_allowed: z.array(z.string()).default([]),
  claims_removed_or_blocked: z.array(z.string()).default([]),
  human_review_questions: z.array(z.string()).default([])
});

export const StructuredDraftGenerationContractSchema = z.object({
  schema_name: z.literal("wilq_content_structured_draft_v1"),
  strict_schema: z.literal(true),
  model_input: StructuredDraftGenerationInputSchema,
  output_schema: z.record(z.string(), z.unknown()),
  system_instruction: z.string(),
  user_instruction: z.string(),
  publish_ready: z.literal(false)
});

export const StructuredDraftGenerationResultSchema = z.object({
  contract: StructuredDraftGenerationContractSchema.nullable().optional(),
  blockers: z.array(ContentWorkflowBlockerSchema).default([])
});

export const StructuredDraftOutputSectionSchema = z.object({
  heading: z.string(),
  body_markdown: z.string(),
  evidence_ids: z.array(z.string()).default([]),
  claims_used: z.array(z.string()).default([])
});

export const StructuredDraftOutputSchema = z.object({
  draft_kind: z.enum(["section_draft", "full_draft"]),
  language: z.literal("pl-PL"),
  title: z.string(),
  meta_title: z.string(),
  meta_description: z.string(),
  h1: z.string(),
  sections: z.array(StructuredDraftOutputSectionSchema),
  faq: z.array(z.string()).default([]),
  cta: z.string(),
  internal_links: z.array(z.string()).default([]),
  source_facts_used: z.array(z.string()).default([]),
  claims_needing_review: z.array(z.string()).default([]),
  forbidden_claims_avoided: z.array(z.string()).default([]),
  human_review_checklist: z.array(z.string()).default([]),
  publish_ready: z.literal(false)
});

export const OpenAIInputMessageSchema = z.object({
  role: z.enum(["system", "user"]),
  content: z.string()
});

export const OpenAIJsonSchemaFormatSchema = z.object({
  type: z.literal("json_schema"),
  name: z.string(),
  strict: z.literal(true),
  schema: z.record(z.string(), z.unknown())
});

export const OpenAITextFormatSchema = z.object({
  format: OpenAIJsonSchemaFormatSchema
});

export const OpenAIStructuredDraftRequestPayloadSchema = z.object({
  model: z.string(),
  input: z.array(OpenAIInputMessageSchema),
  text: OpenAITextFormatSchema,
  temperature: z.number(),
  max_output_tokens: z.number()
});

export const OpenAIStructuredDraftRuntimeBlockerSchema = z.object({
  code: z.string(),
  label: z.string(),
  reason: z.string(),
  next_step: z.string()
});

export const OpenAIStructuredDraftRuntimeResultSchema = z.object({
  status: z.enum(["dry_run_ready", "generated", "blocked"]),
  request_payload: OpenAIStructuredDraftRequestPayloadSchema.nullable().optional(),
  output: StructuredDraftOutputSchema.nullable().optional(),
  external_call_attempted: z.boolean(),
  blockers: z.array(OpenAIStructuredDraftRuntimeBlockerSchema).default([])
});

export const ContentWorkItemStructuredDraftGenerationRequestSchema = z.object({
  item: ContentWorkItemSchema,
  sales_brief: ContentSalesBriefSchema.nullable().optional(),
  claim_ledger: z.unknown().nullable().optional(),
  draft_package: ContentDraftPackageSchema.nullable().optional()
});

export const ContentWorkItemStructuredDraftGenerationResponseSchema = z.object({
  item: ContentWorkItemSchema,
  structured_generation_result: StructuredDraftGenerationResultSchema
});

export const ContentWorkItemStructuredDraftRuntimeRequestSchema = z.object({
  contract: StructuredDraftGenerationContractSchema.nullable().optional(),
  model: z.string().nullable().optional(),
  mode: z.enum(["dry_run", "live"]).default("dry_run")
});

export const ContentWorkItemStructuredDraftRuntimeResponseSchema = z.object({
  runtime_result: OpenAIStructuredDraftRuntimeResultSchema
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
  review: ContentHumanReviewSchema.nullable().optional(),
  blockers: z.array(ContentWorkflowBlockerSchema).default([]),
  wordpress_handoff_allowed: z.boolean()
});

export const ContentWorkItemSnapshotHumanReviewRequestSchema = z.object({
  review: ContentHumanReviewSchema
});

export const ContentWordPressDraftAuditEnvelopeSchema = z.object({
  audit_id: z.string(),
  actor: z.string(),
  reason: z.string(),
  evidence_ids: z.array(z.string()).default([]),
  human_review_id: z.string()
});

export const ContentWorkItemSnapshotAuditRequestSchema = z.object({
  audit: ContentWordPressDraftAuditEnvelopeSchema
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

export const ContentWordPressDraftExecutionPayloadSchema = z.object({
  connector: z.literal("wordpress_ekologus"),
  endpoint_kind: z.literal("posts"),
  post_status: z.literal("draft"),
  title: z.string(),
  content_markdown: z.string(),
  final_canonical_url: z.string(),
  evidence_ids: z.array(z.string()).default([]),
  publish_allowed: z.boolean(),
  destructive_update_allowed: z.boolean()
});

export const ContentWordPressDraftExecutionBlockerSchema = z.object({
  code: z.string(),
  label: z.string(),
  reason: z.string(),
  next_step: z.string()
});

export const ContentWordPressDraftExecutionResultSchema = z.object({
  status: z.enum(["dry_run_ready", "created", "blocked"]),
  mode: z.enum(["dry_run", "live"]),
  payload: ContentWordPressDraftExecutionPayloadSchema.nullable().optional(),
  wordpress_post_id: z.string().nullable().optional(),
  external_write_attempted: z.boolean(),
  blockers: z.array(ContentWordPressDraftExecutionBlockerSchema).default([])
});

export const ContentWorkItemWordPressDraftExecutionRequestSchema = z.object({
  handoff: ContentWordPressDraftHandoffSchema.nullable().optional(),
  draft_package: ContentDraftPackageSchema.nullable().optional(),
  mode: z.enum(["dry_run", "live"]).default("dry_run")
});

export const ContentWorkItemWordPressDraftExecutionResponseSchema = z.object({
  execution_result: ContentWordPressDraftExecutionResultSchema
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

export const ContentWorkflowOperatorStepSchema = z.object({
  id: z.string(),
  title: z.string(),
  status_label: z.string(),
  summary: z.string()
});

export const ContentWorkItemWorkflowSnapshotResponseSchema = z.object({
  preflight: ContentWorkItemPreflightResponseSchema,
  sales_brief: ContentWorkItemSalesBriefResponseSchema,
  draft_package: ContentWorkItemDraftPackageResponseSchema,
  structured_generation: ContentWorkItemStructuredDraftGenerationResponseSchema,
  human_review: ContentWorkItemHumanReviewResponseSchema,
  wordpress_handoff: ContentWorkItemWordPressDraftHandoffResponseSchema,
  measurement_window: ContentWorkItemMeasurementWindowResponseSchema,
  operator_steps: z.array(ContentWorkflowOperatorStepSchema).default([])
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
export type ContentWorkItemStructuredDraftGenerationRequest = z.infer<
  typeof ContentWorkItemStructuredDraftGenerationRequestSchema
>;
export type ContentWorkItemStructuredDraftGenerationResponse = z.infer<
  typeof ContentWorkItemStructuredDraftGenerationResponseSchema
>;
export type ContentWorkItemStructuredDraftRuntimeRequest = z.infer<
  typeof ContentWorkItemStructuredDraftRuntimeRequestSchema
>;
export type ContentWorkItemStructuredDraftRuntimeResponse = z.infer<
  typeof ContentWorkItemStructuredDraftRuntimeResponseSchema
>;
export type ContentWorkItemHumanReviewResponse = z.infer<
  typeof ContentWorkItemHumanReviewResponseSchema
>;
export type ContentWorkItemSnapshotHumanReviewRequest = z.infer<
  typeof ContentWorkItemSnapshotHumanReviewRequestSchema
>;
export type ContentWorkItemSnapshotAuditRequest = z.infer<
  typeof ContentWorkItemSnapshotAuditRequestSchema
>;
export type ContentWorkItemWordPressDraftHandoffResponse = z.infer<
  typeof ContentWorkItemWordPressDraftHandoffResponseSchema
>;
export type ContentWorkItemWordPressDraftExecutionRequest = z.infer<
  typeof ContentWorkItemWordPressDraftExecutionRequestSchema
>;
export type ContentWorkItemWordPressDraftExecutionResponse = z.infer<
  typeof ContentWorkItemWordPressDraftExecutionResponseSchema
>;
export type ContentWorkItemMeasurementWindowResponse = z.infer<
  typeof ContentWorkItemMeasurementWindowResponseSchema
>;
export type ContentWorkflowOperatorStep = z.infer<typeof ContentWorkflowOperatorStepSchema>;
export type ContentWorkItemWorkflowSnapshotResponse = z.infer<
  typeof ContentWorkItemWorkflowSnapshotResponseSchema
>;
