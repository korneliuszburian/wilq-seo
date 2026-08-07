import { z } from "zod";

import { ContentDraftRevisionBindingSchema } from "./actions";
import { MetricFactSchema } from "./connectors";

export const ContentInventoryStatusSchema = z.enum(["missing", "resolved", "blocked"]);
export const ContentOperatorContextSchema = z.object({
  display_label: z.literal("Wilku (lokalny pilot)"),
  request_label: z.literal("operator_local_dashboard"),
  principal_id: z.literal("local_operator"),
  trust_level: z.literal("local_unverified"),
  authentication_status: z.literal("not_configured")
});
export const ContentCanonicalStatusSchema = z.enum(["missing", "resolved", "blocked"]);
export const ContentDuplicateStatusSchema = z.enum([
  "missing",
  "checked",
  "risk_found",
  "blocked"
]);
export const ContentPreflightStatusSchema = z.enum([
  "missing",
  "blocked",
  "plan_allowed",
  "brief_allowed",
  "draft_allowed",
  "handoff_allowed"
]);
export const ContentArtifactStatusSchema = z.enum([
  "missing",
  "ready",
  "approved",
  "blocked"
]);
export const ContentHumanReviewStatusSchema = z.enum([
  "missing",
  "approved",
  "needs_changes",
  "rejected",
  "deferred"
]);
export const ContentAuditStatusSchema = z.enum(["missing", "recorded"]);
export const ContentWordPressHandoffStatusSchema = z.enum([
  "missing",
  "blocked",
  "prepared",
  "draft_created"
]);
export const ContentMeasurementWindowStatusSchema = z.enum([
  "missing",
  "planned",
  "open",
  "ready_for_review",
  "closed"
]);
export const ContentWordPressSectionInventoryStatusSchema = z.enum(["available", "missing"]);

export const ContentWorkItemSchema = z.object({
  id: z.string(),
  topic: z.string(),
  source_public_url: z.string().nullable().optional(),
  final_canonical_url: z.string().nullable().optional(),
  intended_final_url: z.string().nullable().optional(),
  preview_url: z.string().nullable().optional(),
  wordpress_title_or_h1: z.string().nullable().optional(),
  wordpress_section_headings: z.array(z.string()).default([]),
  wordpress_section_count: z.number().nullable().optional(),
  wordpress_section_inventory_status: ContentWordPressSectionInventoryStatusSchema.default(
    "missing"
  ),
  wordpress_content_summary: z.string().nullable().optional(),
  wordpress_content_text: z.string().nullable().optional(),
  wordpress_content_word_count: z.number().int().nonnegative().nullable().optional(),
  wordpress_content_source_kind: z.string().nullable().optional(),
  wordpress_content_extraction_region: z.string().nullable().optional(),
  wordpress_content_material_confidence: z.string().nullable().optional(),
  wordpress_content_inventory_status: z.enum(["available", "missing"]).default("missing"),
  wordpress_content_inventory_note: z.string().nullable().optional(),
  wordpress_acf_section_inventory_status: ContentWordPressSectionInventoryStatusSchema.optional(),
  wordpress_acf_section_inventory_note: z.string().nullable().optional(),
  wordpress_acf_field_names: z.array(z.string()).optional(),
  wordpress_acf_section_headings: z.array(z.string()).optional(),
  wordpress_acf_section_count: z.number().int().nonnegative().nullable().optional(),
  metric_facts: z.array(MetricFactSchema).optional(),
  evidence_ids: z.array(z.string()).default([]),
  source_connectors: z.array(z.string()).default([]),
  total_clicks: z.number().int().nonnegative().nullable().optional(),
  total_impressions: z.number().int().nonnegative().nullable().optional(),
  aggregate_ctr: z.number().nullable().optional(),
  best_average_position: z.number().nullable().optional(),
  query_count: z.number().int().nonnegative().optional(),
  primary_query: z.string().nullable().optional(),
  inventory_status: ContentInventoryStatusSchema,
  canonical_status: ContentCanonicalStatusSchema,
  duplicate_status: ContentDuplicateStatusSchema,
  preflight_status: ContentPreflightStatusSchema.default("missing"),
  preserve_first_plan_status: ContentArtifactStatusSchema.default("missing"),
  sales_brief_status: ContentArtifactStatusSchema.default("missing"),
  sales_brief_id: z.string().nullable().optional(),
  claim_ledger_status: ContentArtifactStatusSchema.default("missing"),
  claim_ledger_id: z.string().nullable().optional(),
  draft_package_status: ContentArtifactStatusSchema.default("missing"),
  draft_package_id: z.string().nullable().optional(),
  human_review_status: ContentHumanReviewStatusSchema.default("missing"),
  human_review_id: z.string().nullable().optional(),
  wordpress_handoff_status: ContentWordPressHandoffStatusSchema.default("missing"),
  wordpress_post_id: z.string().nullable().optional(),
  measurement_window_status: ContentMeasurementWindowStatusSchema.default("missing"),
  measurement_window_id: z.string().nullable().optional(),
  audit_status: ContentAuditStatusSchema.default("missing"),
  audit_id: z.string().nullable().optional()
});

const ContentEvidenceTraceFields = {
  evidence_ids: z.array(z.string()).default([]),
  source_connectors: z.array(z.string()).default([])
};

export const ContentFreshnessAssessmentSchema = z.object({
  state: z.enum(["fresh", "stale", "missing", "blocked"]),
  state_label: z.string().default(""),
  checked_at: z.string().nullable().optional(),
  stale_after_hours: z.number(),
  requires_refresh: z.boolean(),
  missing_connector_ids: z.array(z.string()).default([]),
  blocked_connector_ids: z.array(z.string()).default([]),
  stale_connector_ids: z.array(z.string()).default([]),
  connector_labels_requiring_refresh: z.array(z.string()).default([]),
  connector_refresh_run_ids: z.record(z.string(), z.string()).optional(),
  connector_covered_windows: z.record(
    z.string(),
    z.object({
      date_start: z.string().nullable().optional(),
      date_end: z.string().nullable().optional(),
      completeness: z.string().nullable().optional(),
      cap_or_truncation: z.string().nullable().optional(),
      snapshot_date: z.string().nullable().optional(),
      cadence: z.string().nullable().optional(),
      coverage_scope: z.string().nullable().optional(),
      coverage_count: z.number().nullable().optional(),
      interpretation_caveats: z.array(z.string()).default([])
    })
  ).optional(),
  connector_settlement_states: z.record(z.string(), z.enum(["not_applicable", "settling", "settled", "unknown"])).optional(),
  connector_quality_states: z.record(z.string(), z.enum(["verified", "partial", "unverified", "unknown"])).optional(),
  connector_quality_caveats: z.record(z.string(), z.array(z.string())).optional(),
  summary: z.string(),
  next_step: z.string()
});

const ContentSafeNextStepField = {
  safe_next_step: z.string()
};

const ContentBlockerBaseSchema = z.object({
  code: z.string(),
  label: z.string(),
  reason: z.string(),
  next_step: z.string()
});

export const ContentWorkflowBlockerSchema = ContentBlockerBaseSchema.extend({
  blocks_current_stage: z.boolean().optional()
});

export const ContentWorkItemQueueBlockerSchema = ContentBlockerBaseSchema.extend({
  decision_id: z.string().nullable().optional(),
  ...ContentEvidenceTraceFields
});

export const ContentWorkItemQueueMeasurementReadinessSchema = z.object({
  status: z.string(),
  label: z.string(),
  reason: z.string(),
  source_connectors: ContentEvidenceTraceFields.source_connectors
});

export const ContentWorkItemQueueSearchMetricsSchema = z.object({
  impressions: z.number().int().nullable().optional(),
  clicks: z.number().int().nullable().optional(),
  ctr: z.number().nullable().optional(),
  best_average_position: z.number().nullable().optional(),
  query_count: z.number().int().nonnegative().default(0),
  primary_query: z.string().nullable().optional(),
  comparison_status: z.enum(["available", "not_available", "ambiguous"]).optional(),
  comparison_reason: z.string().optional(),
  comparison_periods: z.array(z.string()).optional(),
  comparison_evidence_ids: z.array(z.string()).optional()
});

export const ContentWorkItemQueueGa4MetricSchema = z.object({
  name: z.string(),
  metric_label: z.string(),
  value: z.union([z.number(), z.string()]),
  period: z.string(),
  evidence_id: z.string(),
  freshness_state: z.enum(["fresh", "stale", "unknown"])
});

export const ContentWorkItemQueueGa4MetricsSchema = z.object({
  status: z.enum(["available", "missing"]).default("missing"),
  metrics: z.array(ContentWorkItemQueueGa4MetricSchema).default([]),
  evidence_ids: z.array(z.string()).default([])
});

export const ContentWorkItemQueuePageInventorySchema = z.object({
  title_or_h1: z.string().nullable().optional(),
  section_count: z.number().int().nonnegative().nullable().optional(),
  section_headings: z.array(z.string().min(1)).default([]),
  section_inventory_status: ContentWordPressSectionInventoryStatusSchema.default("missing"),
  content_inventory_status: z.enum(["available", "missing"]).default("missing"),
  content_summary: z.string().nullable().optional(),
  content_word_count: z.number().int().nonnegative().nullable().optional(),
  acf_section_inventory_status: ContentWordPressSectionInventoryStatusSchema.default("missing"),
  acf_section_inventory_note: z.string().nullable().optional(),
  acf_section_count: z.number().int().nonnegative().nullable().optional(),
  acf_section_headings: z.array(z.string().min(1)).default([])
});

export const ContentRecommendedModeSchema = z.enum([
  "preserve",
  "refresh",
  "merge",
  "create",
  "block"
]);

export const ContentWorkItemQueueCandidateSchema = z.object({
  work_item_id: z.string(),
  decision_id: z.string(),
  title: z.string(),
  topic: z.string(),
  priority: z.number(),
  recommended_mode: ContentRecommendedModeSchema,
  recommended_mode_label: z.string(),
  status_label: z.string(),
  reason: z.string(),
  ...ContentEvidenceTraceFields,
  source_connector_labels: z.array(z.string()).default([]),
  action_ids: z.array(z.string()).default([]),
  action_summary_label: z.string().default(""),
  source_public_url: z.string().nullable().optional(),
  final_canonical_url: z.string().nullable().optional(),
  intended_final_url: z.string().nullable().optional(),
  preview_url: z.string().nullable().optional(),
  preflight_status: z.string(),
  preflight_status_label: z.string(),
  duplicate_canonical_risk_summary: z.string(),
  measurement_readiness: ContentWorkItemQueueMeasurementReadinessSchema,
  search_metrics: ContentWorkItemQueueSearchMetricsSchema.optional(),
  ga4_metrics: ContentWorkItemQueueGa4MetricsSchema.optional(),
  page_inventory: ContentWorkItemQueuePageInventorySchema.optional(),
  safe_next_step: z.string(),
  freshness_assessment: ContentFreshnessAssessmentSchema,
  blockers: z.array(ContentWorkItemQueueBlockerSchema).default([])
});

export const ContentWorkItemQueueResponseSchema = z.object({
  queue_status: z.string(),
  candidate_count: z.number(),
  actionable_candidate_count: z.number(),
  minimum_actionable_candidate_count: z.number(),
  operator_summary: z.string(),
  freshness_assessment: ContentFreshnessAssessmentSchema,
  candidates: z.array(ContentWorkItemQueueCandidateSchema).default([]),
  blockers: z.array(ContentWorkItemQueueBlockerSchema).default([]),
  ...ContentEvidenceTraceFields
});

export const ContentDecisionContextSourceMaterialSchema = z.object({
  status: z.enum(["available", "missing", "blocked", "unknown"]),
  source_kind: z.string().nullable().optional(),
  observed_surfaces: z.array(z.string()).default([]),
  word_count: z.number().int().nonnegative().nullable().optional(),
  section_count: z.number().int().nonnegative().nullable().optional(),
  evidence_ids: z.array(z.string()).default([]),
  caveats: z.array(z.string()).default([])
});

export const ContentDecisionContextSourcePublicSchema = z.object({
  identity_status: z.enum(["observed", "partial", "missing", "unknown"]),
  object_id: z.string().nullable().optional(),
  url: z.string().nullable().optional(),
  title: z.string().nullable().optional(),
  post_type: z.string().nullable().optional(),
  post_status: z.string().nullable().optional(),
  template: z.string().nullable().optional(),
  material: ContentDecisionContextSourceMaterialSchema,
  label: z.string(),
  reason: z.string(),
  technical_reason: z.string().nullable().optional()
});

export const ContentDecisionContextAuthoringTargetSchema = z.object({
  mapping_status: z.enum(["exact", "unverified", "missing"]),
  environment: z.string().nullable().optional(),
  object_id: z.string().nullable().optional(),
  post_type: z.string().nullable().optional(),
  post_status: z.string().nullable().optional(),
  template: z.string().nullable().optional(),
  authoring_surfaces: z.array(z.string()).default([]),
  allowed_operation: z.string().nullable().optional(),
  label: z.string(),
  reason: z.string(),
  technical_reason: z.string().nullable().optional()
});

export const ContentDecisionContextRelationSchema = z.object({
  status: z.enum(["exact", "unverified", "missing"]),
  relation_type: z.enum([
    "same_page",
    "replacement",
    "new_page",
    "migration",
    "structure",
    "unknown"
  ]).default("unknown"),
  label: z.string(),
  reason: z.string(),
  technical_reason: z.string().nullable().optional()
});

export const ContentDecisionContextReadinessAxisSchema = z.object({
  status: z.enum(["ready", "review_required", "refresh_required", "missing", "blocked"]),
  label: z.string(),
  reason: z.string(),
  technical_reason: z.string().nullable().optional(),
  blocker_codes: z.array(z.string()).default([])
});

export const ContentDecisionContextDispositionSchema = z.object({
  status: z.enum(["proposed", "undetermined"]),
  proposed_disposition: z.enum(["refresh_or_merge", "undetermined"]),
  label: z.string(),
  reason: z.string(),
  technical_reason: z.string().nullable().optional()
});

export const ContentDecisionContextServiceSchema = z.object({
  label: z.string().nullable().optional(),
  reason: z.string()
});

export const ContentDecisionContextDeliveryCapabilitySchema = z.object({
  capability: z.enum(["create_draft_only", "manual_handoff", "unsupported"]),
  request_status: z.enum(["blocked", "not_applicable"]),
  label: z.string(),
  reason: z.string(),
  technical_reason: z.string().nullable().optional()
});

export const ContentDecisionContextMeasurementTargetSchema = z.object({
  status: z.string(),
  label: z.string(),
  public_url: z.string().nullable().optional(),
  reason: z.string(),
  technical_reason: z.string().nullable().optional(),
  source_connectors: z.array(z.string()).default([])
});

export const ContentDecisionContextSignalSchema = z.object({
  source_connector: z.string(),
  label: z.string(),
  value: z.union([z.number(), z.string()]),
  freshness_state: z.enum(["fresh", "stale", "unknown"]),
  evidence_ids: z.array(z.string()).default([])
});

export const ContentDecisionContextNextSafeActionSchema = z.object({
  kind: z.enum([
    "refresh_connector",
    "resolve_source_access",
    "map_authoring_target",
    "inspect_object",
    "open_workspace",
    "none"
  ]),
  label: z.string(),
  reason: z.string(),
  connector_id: z.string().nullable().optional()
});

export const ContentDecisionContextDisclosureSchema = z.object({
  id: z.string(),
  label: z.string(),
  summary: z.string()
});

export const ContentDecisionContextAliasSchema = z.object({
  kind: z.enum(["requested_work_item", "inventory_work_item", "decision_work_item"]),
  value: z.string()
});

export const ContentDecisionContextSchema = z.object({
  response_type: z.literal("content_decision_context").default("content_decision_context"),
  contract_version: z.literal("content_decision_context_v1").default("content_decision_context_v1"),
  work_item_id: z.string(),
  work_kind: z.enum(["refresh_existing", "undetermined"]),
  source_public: ContentDecisionContextSourcePublicSchema,
  authoring_target: ContentDecisionContextAuthoringTargetSchema,
  source_target_relation: ContentDecisionContextRelationSchema,
  object_readiness: ContentDecisionContextReadinessAxisSchema,
  decision_disposition: ContentDecisionContextDispositionSchema,
  service: ContentDecisionContextServiceSchema,
  evidence_readiness: ContentDecisionContextReadinessAxisSchema,
  delivery_capability: ContentDecisionContextDeliveryCapabilitySchema,
  measurement_target: ContentDecisionContextMeasurementTargetSchema,
  applicable_signals: z.array(ContentDecisionContextSignalSchema).default([]),
  next_safe_action: ContentDecisionContextNextSafeActionSchema,
  secondary_disclosures: z.array(ContentDecisionContextDisclosureSchema).default([]),
  legacy_aliases: z.array(ContentDecisionContextAliasSchema).default([])
});

export const ContentDocumentWorkspaceSourceSectionSchema = z.object({
  heading: z.string().min(1),
  excerpt: z.string().nullable().optional()
});

export const ContentDocumentWorkspaceSourceSnapshotSchema = z.object({
  status: z.enum(["available", "partial", "unavailable"]),
  title: z.string().nullable().optional(),
  url: z.string().nullable().optional(),
  extraction_method: z.string().nullable().optional(),
  lead: z.string().nullable().optional(),
  content_excerpt: z.string().nullable().optional(),
  ordered_sections: z.array(ContentDocumentWorkspaceSourceSectionSchema).default([]),
  faq_status: z.enum(["observed", "not_observed", "unavailable"]).default("not_observed"),
  cta_status: z.enum(["observed", "not_observed", "unavailable"]).default("not_observed"),
  reason: z.string(),
  caveats: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()).default([])
});

const ContentDocumentSourceProvenanceSchema = z.object({
  source_fact_id: z.string().min(1),
  source_url_or_path: z.string().min(1),
  freshness_date: z.string().min(1),
  reviewer: z.string().min(1).nullable().optional(),
  evidence_ids: z.array(z.string().min(1)).min(1)
});

export const ContentDocumentWorkspaceDocumentSchema = z.object({
  status: z.enum(["not_created", "unreviewed", "needs_changes", "approved", "rejected", "deferred"]),
  revision_id: z.string().nullable().optional(),
  content_digest: z.string().nullable().optional(),
  review_state: z.enum(["unreviewed", "needs_changes", "approved", "rejected", "deferred"]).default("unreviewed"),
  label: z.string(),
  reason: z.string(),
  source_provenance: z.array(ContentDocumentSourceProvenanceSchema).optional(),
  preview: z.lazy(() => ContentDocumentWorkspaceDocumentPreviewSchema).nullable().optional(),
  revision: z.lazy(() => ContentDraftRevisionSchema).nullable().optional(),
  review: z.lazy(() => ContentDraftRevisionReviewSchema).nullable().optional()
}).superRefine((document, context) => {
  if (!document.revision) {
    if (document.review) {
      context.addIssue({ code: z.ZodIssueCode.custom, message: "Document without a revision cannot carry review data." });
    }
    return;
  }
  if (
    document.revision_id !== document.revision.revision_id ||
    document.content_digest !== document.revision.content_digest
  ) {
    context.addIssue({ code: z.ZodIssueCode.custom, message: "Canonical document identity must match its exact revision." });
  }
  if (
    document.review &&
    (document.review.work_item_id !== document.revision.work_item_id ||
      document.review.revision_id !== document.revision.revision_id ||
      document.review.revision_digest !== document.revision.content_digest)
  ) {
    context.addIssue({ code: z.ZodIssueCode.custom, message: "Canonical document review must match its exact revision." });
  }
});

export const ContentDocumentWorkspaceDocumentSectionSchema = z.object({
  section_id: z.string().nullable().optional(),
  heading: z.string().min(1),
  body_markdown: z.string().min(1),
  content_html: z.string().nullable().optional()
});

export const ContentDocumentWorkspaceDocumentPreviewSchema = z.object({
  title: z.string().min(1),
  h1: z.string().nullable().optional(),
  lead: z.string().nullable().optional(),
  sections: z.array(ContentDocumentWorkspaceDocumentSectionSchema).default([]),
  faq_count: z.number().int().nonnegative(),
  cta_count: z.number().int().nonnegative()
});

export const ContentDocumentWorkspaceKnowledgeCardSchema = z.object({
  id: z.string().min(1),
  card_type: z.enum(["service", "buyer_problem", "buyer_trigger", "cta_pattern", "claim_policy", "evidence_requirement", "measurement_sensitive_claim"]).optional(),
  title: z.string().min(1),
  summary: z.string().min(1)
});

export const ContentDocumentWorkspaceDocumentLineageSchema = z.object({
  status: z.enum(["available", "partial", "not_recorded"]),
  source_material_ids: z.array(z.string()).default([]),
  knowledge_cards: z.array(ContentDocumentWorkspaceKnowledgeCardSchema).default([]),
  unresolved_knowledge_card_ids: z.array(z.string()).default([]),
  reason: z.string()
});

export const ContentDocumentWorkspaceNextActionSchema = z.object({
  kind: z.enum(["open_review", "prepare_document", "repair_document", "none"]),
  label: z.string(),
  reason: z.string()
});

export const ContentDocumentWorkspaceComparisonItemSchema = z.object({
  status: z.enum(["same_heading", "source_only", "document_only"]),
  source_heading: z.string().nullable().optional(),
  source_excerpt: z.string().nullable().optional(),
  document_section_id: z.string().nullable().optional(),
  document_heading: z.string().nullable().optional(),
  document_excerpt: z.string().nullable().optional(),
  reason: z.string()
});

export const ContentDocumentWorkspaceComparisonSchema = z.object({
  status: z.enum(["available", "unavailable"]),
  reason: z.string(),
  items: z.array(ContentDocumentWorkspaceComparisonItemSchema).default([])
});

export const ContentRegulatoryReviewCandidateSchema = z.object({
  candidate_id: z.string().min(1),
  source_url: z.string().url(),
  source_title: z.string().min(1),
  observed_on: z.string().min(1),
  requirement_ids: z.array(z.string().min(1)).min(1),
  requirement_labels: z.array(z.string().min(1)).min(1),
  review_status: z.literal("review_required"),
  safe_next_step: z.string().min(1)
});

export const ContentDocumentWorkspaceSchema = z.object({
  response_type: z.literal("content_document_workspace").default("content_document_workspace"),
  contract_version: z.literal("content_document_workspace_v2").default("content_document_workspace_v2"),
  work_item_id: z.string(),
  work_kind: z.literal("refresh_existing"),
  service_label: z.string().nullable().optional(),
  source_snapshot: ContentDocumentWorkspaceSourceSnapshotSchema,
  canonical_document: ContentDocumentWorkspaceDocumentSchema,
  document_lineage: ContentDocumentWorkspaceDocumentLineageSchema,
  comparison: ContentDocumentWorkspaceComparisonSchema,
  next_action: ContentDocumentWorkspaceNextActionSchema,
  regulatory_review_candidates: z.array(ContentRegulatoryReviewCandidateSchema).default([]),
  secondary_disclosures: z.array(z.string()).default([])
});

export const ContentSelectedWorkspaceSchema = z
  .object({
    response_type: z.literal("content_selected_workspace").default("content_selected_workspace"),
    contract_version: z.literal("content_selected_workspace_v1").default("content_selected_workspace_v1"),
    status: z.enum(["ready", "missing"]),
    work_item_id: z.string().min(1),
    operator_journey: z.lazy(() => ContentWorkflowOperatorJourneySchema),
    workspace: ContentDocumentWorkspaceSchema.nullable().optional(),
    reason: z.string().min(1),
    safe_next_step: z.string().min(1)
  })
  .superRefine((value, context) => {
    if (value.status === "ready" && !value.workspace) {
      context.addIssue({ code: z.ZodIssueCode.custom, message: "Ready workspace requires exact workspace data." });
    }
    if (value.status === "missing" && value.workspace) {
      context.addIssue({ code: z.ZodIssueCode.custom, message: "Missing workspace cannot carry workspace data." });
    }
    if (value.workspace && value.workspace.work_item_id !== value.work_item_id) {
      context.addIssue({ code: z.ZodIssueCode.custom, message: "Workspace must match the selected work item." });
    }
  });

export const ContentWorkflowEntryModeSchema = z.object({
  kind: z.enum(["refresh_existing", "new_page"]),
  label: z.string().min(1),
  description: z.string().min(1),
  route: z.enum(["refresh_existing", "new_page"])
});

export const ContentWorkflowEntryFactSchema = z.object({
  label: z.string().min(1),
  value: z.string().min(1)
});

export const ContentWorkflowEntryRecommendationSchema = z.object({
  work_item_id: z.string().min(1),
  title: z.string().min(1),
  url: z.string().url(),
  reason: z.string().min(1),
  facts: z.array(ContentWorkflowEntryFactSchema).default([])
});

export const ContentWorkflowEntrySearchResultSchema = z.object({
  work_item_id: z.string().min(1),
  title: z.string().min(1),
  url: z.string().url(),
  material_label: z.string().min(1)
});

export const ContentWorkflowEntryResponseSchema = z.object({
  response_type: z.literal("content_workflow_entry").default("content_workflow_entry"),
  refresh_existing: ContentWorkflowEntryModeSchema,
  new_page: ContentWorkflowEntryModeSchema,
  recommendations: z.array(ContentWorkflowEntryRecommendationSchema).max(3).default([]),
  search_query: z.string().nullable().optional(),
  search_results: z.array(ContentWorkflowEntrySearchResultSchema).max(10).default([]),
  browse_inventory_label: z.string().min(1)
});

export const ContentNewPageBriefInputSchema = z.object({
  title: z.string().min(3).max(160),
  purpose: z.string().min(8).max(800),
  service: z.string().min(2).max(160),
  audience: z.string().min(3).max(300),
  search_intent: z.string().min(3).max(300),
  proposed_ia_location: z.string().min(3).max(300),
  topic_candidate_id: z.string().min(1).nullable().optional(),
  topic_candidate_digest: z.string().regex(/^[0-9a-f]{64}$/).nullable().optional()
}).strict().superRefine((brief, context) => {
  const hasId = brief.topic_candidate_id != null;
  const hasDigest = brief.topic_candidate_digest != null;
  if (hasId !== hasDigest) {
    context.addIssue({ code: z.ZodIssueCode.custom, message: "A source-backed topic needs both its candidate ID and exact digest." });
  }
});

export const ContentNewPageBriefSchema = ContentNewPageBriefInputSchema.extend({
  brief_id: z.string().min(1),
  brief_digest: z.string().length(64),
  created_at: z.string(),
  work_kind: z.literal("new_page"),
  topic_evidence_ids: z.array(z.string()).default([])
}).superRefine((brief, context) => {
  if (brief.topic_candidate_id == null && brief.topic_evidence_ids.length) {
    context.addIssue({ code: z.ZodIssueCode.custom, message: "A manual new-page brief cannot claim topic evidence." });
  }
  if (brief.topic_candidate_id != null && !brief.topic_evidence_ids.length) {
    context.addIssue({ code: z.ZodIssueCode.custom, message: "A selected topic candidate needs persisted evidence." });
  }
});

export const ContentNewPageTopicCandidateSchema = z.object({
  candidate_id: z.string().min(1),
  candidate_digest: z.string().regex(/^[0-9a-f]{64}$/),
  title: z.string().min(3).max(160),
  topic: z.string().min(3).max(160),
  rationale: z.string().min(1),
  source_connectors: z.array(z.string()).min(2),
  evidence_ids: z.array(z.string()).min(2)
});

export const ContentNewPageTopicRecommendationsSchema = z.object({
  response_type: z.literal("content_new_page_topic_recommendations"),
  contract_version: z.literal("content_new_page_topic_recommendations_v1"),
  status: z.enum(["ready", "no_qualified_topics", "blocked"]),
  title: z.string().min(1),
  reason: z.string().min(1),
  safe_next_step: z.string().min(1),
  candidates: z.array(ContentNewPageTopicCandidateSchema).default([]),
  source_connectors: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()).default([])
}).superRefine((recommendations, context) => {
  if (recommendations.status === "ready" && !recommendations.candidates.length) {
    context.addIssue({ code: z.ZodIssueCode.custom, message: "Ready topic recommendations need at least one candidate." });
  }
  if (recommendations.status !== "ready" && recommendations.candidates.length) {
    context.addIssue({ code: z.ZodIssueCode.custom, message: "A non-ready topic recommendation response cannot expose candidates." });
  }
});

export const ContentNewPageOverlapCandidateSchema = z.object({
  title: z.string().min(1),
  url: z.string().url(),
  match_kind: z.enum(["same_title", "shared_intent", "shared_service"]),
  evidence_ids: z.array(z.string()).default([])
});

export const ContentNewPageOverlapGuardSchema = z.object({
  disposition: z.enum([
    "no_conflict",
    "differentiate",
    "reuse",
    "merge",
    "human_decision_required"
  ]),
  label: z.string().min(1),
  reason: z.string().min(1),
  caveat: z.string().min(1),
  evidence_ids: z.array(z.string()).default([]),
  candidates: z.array(ContentNewPageOverlapCandidateSchema).default([])
});

export const ContentNewPageServiceOptionSchema = z.object({
  service_card_id: z.string().min(1),
  label: z.string().min(1),
  summary: z.string().min(1),
  evidence_ids: z.array(z.string()).default([])
});

export const ContentNewPageFoundationCommandSchema = z.object({
  expected_brief_digest: z.string().regex(/^[0-9a-f]{64}$/),
  expected_overlap_digest: z.string().regex(/^[0-9a-f]{64}$/),
  service_card_id: z.string().min(1),
  confirmed_by: z.string().min(2).max(160)
}).strict();

export const ContentNewPagePlanningFoundationSchema = z.object({
  foundation_id: z.string().min(1),
  work_item_id: z.string().min(1),
  brief_id: z.string().min(1),
  brief_digest: z.string().regex(/^[0-9a-f]{64}$/),
  overlap_digest: z.string().regex(/^[0-9a-f]{64}$/),
  overlap_evidence_ids: z.array(z.string()).default([]),
  service_card_id: z.string().min(1),
  service_card_digest: z.string().regex(/^[0-9a-f]{64}$/),
  service_label: z.string().min(1),
  service_evidence_ids: z.array(z.string()).default([]),
  confirmed_by: z.string().min(2),
  created_at: z.string()
});

export const ContentNewPageDocumentIdentitySchema = z.object({
  work_item_id: z.string().min(1),
  work_kind: z.literal("new_page"),
  brief_id: z.string().min(1),
  brief_digest: z.string().regex(/^[0-9a-f]{64}$/),
  foundation_id: z.string().min(1),
  service_card_id: z.string().min(1),
  service_card_digest: z.string().regex(/^[0-9a-f]{64}$/),
  proposed_ia_location: z.string().trim().min(3),
  public_source_status: z.literal("not_applicable"),
  public_source_url: z.null(),
  public_source_evidence_ids: z.array(z.string()).length(0),
  document_status: z.literal("not_created"),
  public_deployment_status: z.literal("not_confirmed"),
  public_deployment_id: z.null()
});

export const ContentNewPagePlanningProposalRequestSchema = z.object({
  expected_planning_input_digest: z.string().regex(/^[0-9a-f]{64}$/),
  requested_by: z.string().trim().min(1).max(160),
  operator_hint: z.string().max(500).default("")
}).strict();

export const ContentNewPageFoundationResultSchema = z.object({
  status: z.enum(["created", "idempotent", "blocked", "conflict"]),
  foundation: ContentNewPagePlanningFoundationSchema.nullable().optional(),
  reason: z.string().min(1),
  safe_next_step: z.string().min(1)
});

export const ContentNewPageBriefWorkspaceSchema = z.object({
  response_type: z.literal("content_new_page_brief_workspace"),
  contract_version: z.literal("content_new_page_brief_workspace_v2"),
  brief: ContentNewPageBriefSchema,
  overlap_guard: ContentNewPageOverlapGuardSchema,
  overlap_digest: z.string().regex(/^[0-9a-f]{64}$/),
  service_options: z.array(ContentNewPageServiceOptionSchema).default([]),
  foundation: ContentNewPagePlanningFoundationSchema.nullable().optional(),
  review_status: z.literal("blocked"),
  review_reason: z.string().min(1),
  next_action_label: z.string().min(1)
});

export const ContentTargetAuthoringRelationshipItemSchema = z.object({
  relationship_id: z.number().int().positive(),
  label: z.string().min(1)
});

export const ContentTargetAuthoringRelationshipSchema = z.object({
  field_name: z.string().min(1),
  item_kind: z.literal("integer_id").default("integer_id"),
  status: z.enum(["available", "unavailable"]).default("unavailable"),
  source_ref: z.string().default(""),
  items: z.array(ContentTargetAuthoringRelationshipItemSchema).default([]),
  reason: z.string().default("")
});

export const ContentTargetAuthoringLayoutSchema = z.object({
  name: z.string().min(1),
  section_index: z.number().int().positive().nullable().optional(),
  label: z.string().default(""),
  fields: z.array(z.string()).default([]),
  schema_fields: z.array(z.string()).default([]),
  writable_fields: z.array(z.string()).default([]),
  relationships: z.array(ContentTargetAuthoringRelationshipSchema).default([])
});

export const ContentTargetAuthoringSurfaceSchema = z.object({
  kind: z.enum(["acf_flexible_content", "wordpress_post_content"]),
  root_field: z.string().min(1),
  layouts: z.array(ContentTargetAuthoringLayoutSchema).default([]),
  schema_status: z.enum(["available", "unavailable"]).default("unavailable"),
  schema_digest: z.string().regex(/^[0-9a-f]{64}$/).nullable().optional(),
  schema_source_ref: z.string().default(""),
  schema_reason: z.string().default(""),
  source_acf_digest: z.string().regex(/^[0-9a-f]{64}$/).nullable().optional(),
  source_acf_fields_digest: z.string().regex(/^[0-9a-f]{64}$/).nullable().optional(),
  source_acf_root_field_count: z.number().int().nonnegative().nullable().optional(),
  source_acf_row_count: z.number().int().nonnegative().nullable().optional(),
  write_profile_status: z.enum(["ready", "not_required", "unavailable"]).default("unavailable"),
  write_profile_reason: z.string().default("")
});

export const ContentTargetContractSchema = z.object({
  environment: z.string().min(1),
  object_id: z.string().min(1),
  url: z.string().url(),
  post_type: z.string().min(1),
  rest_endpoint: z.string().regex(/^[a-z0-9_-]+$/).default("pages"),
  post_status: z.string().min(1),
  modified: z.string(),
  template: z.string().nullable().optional(),
  authority: z.literal("observation_only"),
  write_authorized: z.literal(false),
  authoring_surface: ContentTargetAuthoringSurfaceSchema.nullable().optional()
});

export const ContentTargetObservationEvidenceSchema = z.object({
  evidence_id: z.string().min(1),
  connector_id: z.string().min(1),
  object_id: z.string().min(1),
  post_type: z.string().min(1),
  url: z.string().url(),
  post_status: z.string().min(1),
  modified: z.string(),
  observed_at: z.string().datetime({ offset: true })
});

export const ContentTargetDiscoveryCandidateSchema = z.object({
  object_id: z.string().min(1),
  url: z.string().url(),
  post_type: z.string().min(1),
  post_status: z.string().min(1),
  observation_evidence: ContentTargetObservationEvidenceSchema
});

export const ContentTargetDiscoveryTargetSchema = z.object({
  object_id: z.string().min(1),
  url: z.string().url(),
  post_type: z.string().min(1),
  post_status: z.string().min(1),
  template: z.string().nullable().optional(),
  observed_surfaces: z.array(z.string()).default([]),
  target_contract: ContentTargetContractSchema,
  target_contract_digest: z.string().length(64),
  observation_evidence: ContentTargetObservationEvidenceSchema
});

export const ContentTargetDiscoverySchema = z.object({
  response_type: z.literal("content_target_discovery"),
  contract_version: z.literal("content_target_discovery_v2"),
  work_item_id: z.string().min(1),
  public_url: z.string().url().nullable().optional(),
  relation_status: z.enum(["partial", "ambiguous", "unavailable"]),
  label: z.string().min(1),
  reason: z.string().min(1),
  target: ContentTargetDiscoveryTargetSchema.nullable().optional(),
  candidates: z.array(ContentTargetDiscoveryCandidateSchema).default([]),
  evidence_ids: z.array(z.string()).default([]),
  caveats: z.array(z.string()).default([])
});

export const ContentTargetMappingRevisionSchema = z.object({
  revision_id: z.string().min(1),
  content_digest: z.string().regex(/^[0-9a-f]{64}$/)
});

export const ContentTargetMappingTargetSchema = z.object({
  target_contract: ContentTargetContractSchema,
  target_contract_digest: z.string().length(64),
  observation_evidence: ContentTargetObservationEvidenceSchema
});

export const ContentTargetMappingSourceFieldSchema = z.object({
  key: z.string().min(1),
  label: z.string().min(1)
});

export const ContentTargetMappingFieldBindingSchema = z.object({
  source_field: z.string().min(1),
  target_field: z.string().min(1)
});

export const ContentTargetMappingSelectionSchema = z.object({
  component_id: z.string().min(1),
  layout_name: z.string().min(1),
  target_section_index: z.number().int().positive().nullable().optional(),
  field_bindings: z.array(ContentTargetMappingFieldBindingSchema).min(1)
});

export const ContentTargetMappingConfirmationCommandSchema = z.object({
  expected_revision_digest: z.string().regex(/^[0-9a-f]{64}$/),
  expected_target_contract_digest: z.string().regex(/^[0-9a-f]{64}$/),
  expected_binding_digest: z.string().regex(/^[0-9a-f]{64}$/),
  confirmed_by: z.string().min(1),
  delivery_scope: z.enum(["full_document", "selected_components"]).default("full_document"),
  selections: z.array(ContentTargetMappingSelectionSchema).min(1)
});

export const ContentTargetMappingConfirmationSchema = z.object({
  confirmation_id: z.string().min(1),
  confirmation_number: z.number().int().min(1),
  work_item_id: z.string().min(1),
  revision: ContentTargetMappingRevisionSchema,
  target_contract_digest: z.string().regex(/^[0-9a-f]{64}$/),
  binding_digest: z.string().regex(/^[0-9a-f]{64}$/),
  delivery_scope: z.enum(["full_document", "selected_components"]).default("full_document"),
  selections: z.array(ContentTargetMappingSelectionSchema).min(1),
  confirmed_by: z.string().min(1),
  confirmation_digest: z.string().regex(/^[0-9a-f]{64}$/),
  created_at: z.string().min(1)
});

export const ContentTargetMappingConfirmationResultSchema = z.object({
  status: z.enum(["created", "idempotent"]),
  confirmation: ContentTargetMappingConfirmationSchema
});

export const ContentTargetDraftPreviewFieldSchema = z.object({
  target_field: z.string().min(1),
  source_field: z.string().min(1),
  value: z.string().min(1),
  value_kind: z.enum(["plain_text", "html", "url"])
});

export const ContentTargetDraftPreviewComponentSchema = z.object({
  component_id: z.string().min(1),
  label: z.string().min(1),
  layout_name: z.string().min(1),
  target_section_index: z.number().int().nonnegative().nullable().optional(),
  fields: z.array(ContentTargetDraftPreviewFieldSchema).min(1)
});

export const ContentTargetDraftPreviewBlockerSchema = z.object({
  code: z.enum(["mapping_not_confirmed", "mapping_stale"]),
  label: z.string().min(1),
  reason: z.string().min(1),
  next_step: z.string().min(1)
});

export const ContentTargetDraftPreviewPreservedSourceSummarySchema = z.object({
  label: z.string().min(1),
  source_root_field_count: z.number().int().positive(),
  source_row_count: z.number().int().positive(),
  changed_row_count: z.number().int().positive(),
  unchanged_row_count: z.number().int().nonnegative(),
  preserved_sibling_root_field_count: z.number().int().nonnegative()
});

export const ContentTargetDraftPreviewSchema = z.object({
  response_type: z.literal("content_target_draft_preview"),
  contract_version: z.literal("content_target_draft_preview_v1"),
  work_item_id: z.string().min(1),
  revision: ContentTargetMappingRevisionSchema,
  status: z.enum(["ready", "blocked"]),
  target: ContentTargetMappingTargetSchema.nullable().optional(),
  confirmation: ContentTargetMappingConfirmationSchema.nullable().optional(),
  root_field: z.string().min(1).nullable().optional(),
  delivery_scope: z.enum(["full_document", "selected_components"]).default("full_document"),
  draft_title: z.string().min(1).nullable().optional(),
  components: z.array(ContentTargetDraftPreviewComponentSchema).default([]),
  preserved_source_summary: ContentTargetDraftPreviewPreservedSourceSummarySchema.nullable().optional(),
  payload_digest: z.string().regex(/^[0-9a-f]{64}$/).nullable().optional(),
  blockers: z.array(ContentTargetDraftPreviewBlockerSchema).default([]),
  caveats: z.array(z.string()).default([])
});

export const ContentTargetDraftActionCommandSchema = z.object({
  expected_revision_digest: z.string().regex(/^[0-9a-f]{64}$/),
  expected_target_contract_digest: z.string().regex(/^[0-9a-f]{64}$/),
  expected_confirmation_digest: z.string().regex(/^[0-9a-f]{64}$/),
  expected_payload_digest: z.string().regex(/^[0-9a-f]{64}$/),
  requested_by: z.string().min(1).max(200)
});

export const ContentNewPageDeliveryReadinessSchema = z.object({
  response_type: z.literal("content_new_page_delivery_readiness"),
  contract_version: z.literal("content_new_page_delivery_readiness_v1"),
  status: z.enum(["ready_for_action", "blocked"]),
  work_item_id: z.string().min(1),
  brief_id: z.string().min(1),
  brief_digest: z.string().regex(/^[0-9a-f]{64}$/),
  foundation_id: z.string().min(1),
  service_card_id: z.string().min(1),
  service_card_digest: z.string().regex(/^[0-9a-f]{64}$/),
  revision_id: z.string().min(1).nullable().optional(),
  revision_digest: z.string().regex(/^[0-9a-f]{64}$/).nullable().optional(),
  allowed_content_types: z.array(z.enum(["page", "post"])).default([]),
  authoring_profile_digest: z.string().regex(/^[0-9a-f]{64}$/).nullable().optional(),
  evidence_ids: z.array(z.string().min(1)).default([]),
  blockers: z.array(z.string().min(1)).default([]),
  safe_next_step: z.string().min(1)
}).superRefine((readiness, context) => {
  if (readiness.status === "ready_for_action") {
    if (!readiness.revision_id || !readiness.revision_digest || !readiness.authoring_profile_digest || !readiness.allowed_content_types.length || !readiness.evidence_ids.length || readiness.blockers.length) {
      context.addIssue({ code: z.ZodIssueCode.custom, message: "Ready new-page delivery requires exact revision and observed capability." });
    }
  } else if (readiness.revision_id != null || readiness.revision_digest != null) {
    context.addIssue({ code: z.ZodIssueCode.custom, message: "Blocked new-page delivery cannot expose an action revision." });
  }
});

export const ContentNewPageDraftActionCommandSchema = z.object({
  expected_revision_digest: z.string().regex(/^[0-9a-f]{64}$/),
  expected_authoring_profile_digest: z.string().regex(/^[0-9a-f]{64}$/),
  content_type: z.enum(["page", "post"]),
  requested_by: z.string().min(1).max(200)
});

export const ContentTargetMappingComponentSchema = z.object({
  component_id: z.string().min(1),
  kind: z.enum(["document_title", "document_content", "page_assets", "rich_text", "faq", "cta", "internal_link"]),
  label: z.string().min(1),
  status: z.enum(["mapped", "human_only", "blocked"]),
  reason: z.string().min(1),
  target_root_field: z.string().nullable().optional(),
  available_layouts: z.array(z.string()).default([]),
  source_fields: z.array(ContentTargetMappingSourceFieldSchema).default([])
});

export const ContentTargetMappingBlockerSchema = z.object({
  code: z.enum([
    "revision_not_approved",
    "target_unavailable",
    "target_ambiguous",
    "authoring_surface_unknown",
    "acf_write_profile_unavailable"
  ]),
  label: z.string().min(1),
  reason: z.string().min(1),
  next_step: z.string().min(1)
});

export const ContentTargetMappingPreviewSchema = z.object({
  response_type: z.literal("content_target_mapping_preview"),
  contract_version: z.literal("content_target_mapping_preview_v1"),
  work_item_id: z.string().min(1),
  revision: ContentTargetMappingRevisionSchema,
  status: z.enum(["ready_for_human_mapping", "blocked"]),
  target: ContentTargetMappingTargetSchema.nullable().optional(),
  binding_digest: z.string().regex(/^[0-9a-f]{64}$/).nullable().optional(),
  components: z.array(ContentTargetMappingComponentSchema).default([]),
  confirmation: ContentTargetMappingConfirmationSchema.nullable().optional(),
  blockers: z.array(ContentTargetMappingBlockerSchema).default([]),
  caveats: z.array(z.string()).default([])
});

export const ContentInventoryRecordSchema = z.object({
  id: z.string(),
  url: z.string(),
  final_canonical_url: z.string().nullable().optional(),
  intended_final_url: z.string().nullable().optional(),
  preview_url: z.string().nullable().optional(),
  content_status: z.string(),
  source_connectors: z.array(z.string()).default([]),
  source_fact_ids: z.array(z.string()).default([]),
  source_material_ids: z.array(z.string()).default([]),
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

export const ContentInventoryDuplicateRiskSchema = z.enum([
  "unknown",
  "clear",
  "review_required",
  "high"
]);

export const ContentClaimTypeSchema = z.enum([
  "service_claim",
  "legal_requirement_claim",
  "risk_claim",
  "guarantee_claim",
  "performance_claim",
  "seo_claim",
  "business_outcome_claim",
  "environmental_claim",
  "product_claim"
]);

export const ContentClaimStatusSchema = z.enum([
  "allowed_with_evidence",
  "allowed_general",
  "needs_human_review",
  "blocked",
  "blocked_until_measurement"
]);

export const ContentClaimStrengthSchema = z.enum(["strong", "weak"]);

export const ContentClaimReferenceSchema = z.object({
  claim_id: z.string().optional(),
  id: z.string().optional(),
  claim_text: z.string().optional(),
  claim_type: ContentClaimTypeSchema.optional(),
  status: ContentClaimStatusSchema.optional(),
  evidence_ids: z.array(z.string()).optional(),
  source_connectors: z.array(z.string()).optional(),
  reviewer_id: z.string().nullable().optional(),
  reason: z.string().optional()
});

export const ContentClaimLedgerEntrySchema = z.object({
  id: z.string(),
  claim_text: z.string(),
  claim_type: ContentClaimTypeSchema,
  status: ContentClaimStatusSchema,
  strength: ContentClaimStrengthSchema.default("strong"),
  required: z.boolean().default(false),
  evidence_ids: z.array(z.string()).default([]),
  source_connectors: z.array(z.string()).default([]),
  reason: z.string(),
  reviewer_id: z.string().nullable().optional()
});

export const ContentClaimLedgerSchema = z.object({
  id: z.string(),
  work_item_id: z.string(),
  entries: z.array(ContentClaimLedgerEntrySchema).default([]),
  reviewed_by: z.string().nullable().optional()
});

export const ContentSalesBriefSourceFactSchema = z.object({
  evidence_id: z.string(),
  source_connector: z.string(),
  summary: z.string(),
  source_fact_ids: z.array(z.string()).default([]),
  source_material_ids: z.array(z.string()).default([])
});

export const ContentSalesBriefSeedSchema = z.object({
  target_reader: z.string(),
  buyer_problem: z.string(),
  buyer_trigger: z.string(),
  search_intent: z.string(),
  service_fit: z.string(),
  h1_direction: z.string(),
  h2_direction: z.array(z.string()).default([]),
  faq_direction: z.array(z.string()).default([]),
  cta_direction: z.string(),
  internal_link_direction: z.array(z.string()).default([]),
  source_facts: z.array(ContentSalesBriefSourceFactSchema).default([]),
  missing_evidence: z.array(z.string()).default([])
});

export const ContentSalesBriefOperationsContextSchema = z.object({
  enrichment_id: z.string(),
  intent_label: z.string(),
  recommended_mode: ContentRecommendedModeSchema,
  safe_next_step: z.string(),
  source_fact_ids: z.array(z.string()).default([])
});

export const ContentKnowledgeConstraintTypeSchema = z.enum([
  "service_fit",
  "evidence_requirement",
  "allowed_with_evidence",
  "needs_human_review",
  "blocked",
  "blocked_until_measurement",
  "source_backed_review_required",
  "stale"
]);

export const ContentSalesBriefKnowledgeConstraintSchema = z.object({
  card_id: z.string(),
  constraint_type: ContentKnowledgeConstraintTypeSchema,
  label: z.string(),
  reason: z.string(),
  evidence_ids: z.array(z.string()).default([])
});

export const ContentSalesBriefSignalQualitySchema = z.object({
  status: z.enum(["strong", "review_required", "thin"]),
  status_label: z.string(),
  reason: z.string(),
  evidence_id_count: z.number(),
  source_connector_count: z.number(),
  source_fact_count: z.number(),
  missing_evidence_count: z.number(),
  knowledge_constraint_count: z.number(),
  review_required_knowledge_card_count: z.number(),
  measurement_baseline_ready: z.boolean(),
  safe_next_step: z.string()
});

export const ContentKnowledgeClaimRuleSchema = z.object({
  id: z.string(),
  claim_type: z.string(),
  status: z.enum([
    "allowed_with_evidence",
    "needs_human_review",
    "blocked",
    "blocked_until_measurement"
  ]),
  label: z.string(),
  reason: z.string(),
  required_evidence_types: z.array(z.string()).default([])
});

export const ContentKnowledgeLifecycleStatusSchema = z.enum([
  "seeded_contract_proof",
  "source_backed_review_required",
  "approved_current",
  "stale",
  "rejected"
]);

export const ContentKnowledgeCardSchema = z.object({
  id: z.string(),
  card_type: z.enum([
    "service",
    "buyer_problem",
    "buyer_trigger",
    "cta_pattern",
    "claim_policy",
    "evidence_requirement",
    "measurement_sensitive_claim",
    "regulatory_source"
  ]),
  title: z.string(),
  summary: z.string(),
  service_fit_terms: z.array(z.string()).default([]),
  buyer_problem_terms: z.array(z.string()).default([]),
  buyer_triggers: z.array(z.string()).default([]),
  cta_patterns: z.array(z.string()).default([]),
  allowed_claims: z.array(z.string()).default([]),
  claims_needing_review: z.array(ContentKnowledgeClaimRuleSchema).default([]),
  forbidden_claims: z.array(ContentKnowledgeClaimRuleSchema).default([]),
  evidence_requirements: z.array(z.string()).default([]),
  measurement_sensitive_claims: z.array(ContentKnowledgeClaimRuleSchema).default([]),
  source_lineage: z.array(z.string()).default([]),
  source_fact_ids: z.array(z.string()).default([]),
  source_material_ids: z.array(z.string()).default([]),
  source_connectors: z.array(z.string()).default([]),
  lifecycle_status: ContentKnowledgeLifecycleStatusSchema.nullable().optional(),
  confidence: z.number(),
  freshness: z.string(),
  usage_notes: z.array(z.string()).default([])
});

export const KnowledgeSourceFactViewSchema = z.object({
  source_id: z.string(),
  source_type: z.string(),
  privacy_class: z.string(),
  source_url_or_path: z.string(),
  extracted_fact: z.string(),
  scope: z.string(),
  freshness_date: z.string(),
  confidence: z.number(),
  review_status: z.string(),
  generation_status: z.enum(["eligible", "blocked_review_required"]),
  reviewer: z.string().nullable().optional(),
  evidence_ids: z.array(z.string()).default([]),
  source_connectors: z.array(z.string()).default([]),
  target_card_id: z.string(),
  target_card_title: z.string(),
  blocked_claims: z.array(z.string()).default([]),
  usage_notes: z.array(z.string()).default([])
});

export const KnowledgeSourceMaterialViewSchema = z.object({
  source_id: z.string(),
  file_name: z.string(),
  title: z.string(),
  kind: z.string(),
  word_count: z.number().int().nonnegative(),
  digest_prefix: z.string(),
  privacy_class: z.string(),
  import_status: z.string(),
  source_path: z.string().optional()
});

export const KnowledgeSourceMaterialReadinessSchema = z.object({
  status: z.enum(["ready", "import_pending", "excerpt_review_required"]),
  total_count: z.number().int().nonnegative(),
  imported_count: z.number().int().nonnegative(),
  import_pending_count: z.number().int().nonnegative(),
  excerpt_review_required_count: z.number().int().nonnegative(),
  ready_for_generation: z.boolean(),
  imported_materials: z.array(KnowledgeSourceMaterialViewSchema).optional(),
  pending_materials: z.array(KnowledgeSourceMaterialViewSchema).optional(),
  excerpt_review_materials: z.array(KnowledgeSourceMaterialViewSchema).optional(),
  blocker: z.string().nullable().optional(),
  next_step: z.string()
});

export const ContentKnowledgeProductionDepthReadinessSchema = z.object({
  status: z.enum([
    "seeded_contract_proof",
    "source_backed_review_required",
    "production_depth"
  ]),
  status_label: z.string(),
  ready_for_daily_content: z.boolean(),
  seeded_card_count: z.number(),
  source_backed_review_required_count: z.number(),
  production_depth_card_count: z.number(),
  blocker_labels: z.array(z.string()).default([])
});

export const ContentKnowledgeCardBlockerSchema = z.object({
  code: z.string(),
  label: z.string(),
  reason: z.string(),
  next_step: z.string(),
  work_item_id: z.string().nullable().optional(),
  required_card_type: z
    .enum([
      "service",
      "buyer_problem",
      "buyer_trigger",
      "cta_pattern",
      "claim_policy",
      "evidence_requirement",
      "measurement_sensitive_claim"
    ])
    .nullable()
    .optional()
});

export const ContentKnowledgeCardsResponseSchema = z.object({
  cards: z.array(ContentKnowledgeCardSchema).default([]),
  card_count: z.number(),
  source_lineage: z.array(z.string()).default([]),
  production_depth_readiness: ContentKnowledgeProductionDepthReadinessSchema
});

export const ContentKnowledgeCardMatchSchema = z.object({
  work_item_id: z.string(),
  service_card: ContentKnowledgeCardSchema.nullable().optional(),
  buyer_problem_cards: z.array(ContentKnowledgeCardSchema).default([]),
  cta_cards: z.array(ContentKnowledgeCardSchema).default([]),
  claim_policy_cards: z.array(ContentKnowledgeCardSchema).default([]),
  evidence_requirement_cards: z.array(ContentKnowledgeCardSchema).default([]),
  measurement_sensitive_cards: z.array(ContentKnowledgeCardSchema).default([]),
  blockers: z.array(ContentKnowledgeCardBlockerSchema).default([])
});

export const ContentServiceProfileReviewPolicySchema = z.object({
  can_edit_cards: z.boolean(),
  can_promote_facts: z.boolean(),
  can_request_review: z.boolean(),
  review_required_label: z.string(),
  blocked_write_reason: z.string()
});

export const ContentServiceProfileCoverageSummarySchema = z.object({
  card_count: z.number(),
  service_card_count: z.number(),
  seeded_contract_proof_count: z.number(),
  source_backed_review_required_count: z.number(),
  approved_current_count: z.number(),
  stale_count: z.number(),
  rejected_count: z.number(),
  private_candidate_count: z.number(),
  missing_required_area_count: z.number(),
  ready_for_daily_content: z.boolean(),
  status_label: z.string(),
  safe_next_step: z.string()
});

export const ContentServiceProfileServiceSectionSchema = z.object({
  card_id: z.string(),
  title: z.string(),
  status: ContentKnowledgeLifecycleStatusSchema,
  status_label: z.string(),
  summary: z.string(),
  source_fact_ids: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()).default([]),
  source_connector_labels: z.array(z.string()).default([]),
  source_lineage_labels: z.array(z.string()).default([]),
  freshness_label: z.string(),
  confidence_label: z.string(),
  service_fit_terms: z.array(z.string()).default([]),
  buyer_problem_terms: z.array(z.string()).default([]),
  buyer_triggers: z.array(z.string()).default([]),
  cta_patterns: z.array(z.string()).default([]),
  allowed_claims: z.array(z.string()).default([]),
  claims_needing_review: z.array(ContentKnowledgeClaimRuleSchema).default([]),
  forbidden_claims: z.array(ContentKnowledgeClaimRuleSchema).default([]),
  evidence_requirements: z.array(z.string()).default([]),
  usage_notes: z.array(z.string()).default([]),
  safe_next_step: z.string(),
  review_request_hint: z.string()
});

export const ContentServiceProfilePolicySectionSchema = z.object({
  card_id: z.string(),
  title: z.string(),
  status: ContentKnowledgeLifecycleStatusSchema,
  claims_needing_review: z.array(ContentKnowledgeClaimRuleSchema).default([]),
  forbidden_claims: z.array(ContentKnowledgeClaimRuleSchema).default([]),
  measurement_sensitive_claims: z.array(ContentKnowledgeClaimRuleSchema).default([]),
  evidence_requirements: z.array(z.string()).default([]),
  safe_next_step: z.string()
});

export const ContentServiceProfilePrivateSourceProposalSummarySchema = z.object({
  proposal_protocol_available: z.boolean(),
  proposal_count: z.number(),
  service_proposal_count: z.number(),
  claim_policy_proposal_count: z.number(),
  evidence_requirement_proposal_count: z.number(),
  review_required_count: z.number(),
  approved_count: z.number(),
  promotion_ready: z.boolean(),
  promotion_checklist: z.array(z.string()).default([]),
  promotion_blocked_reason: z.string(),
  proposal_source_labels: z.array(z.string()).default([]),
  review_required_proposal_ids: z.array(z.string()).default([]),
  redacted: z.boolean(),
  safe_next_step: z.string()
});

export const ContentServiceProfilePrivateSourceProposalReviewStatusSchema = z.enum([
  "review_required",
  "approved",
  "rejected",
  "stale"
]);

export const ContentServiceProfilePrivateSourceProposalSupportLevelSchema = z.enum([
  "direct",
  "partial",
  "background",
  "conflicting"
]);

export const ContentServiceProfilePrivateSourceProposalRiskTierSchema = z.enum([
  "low",
  "medium",
  "high",
  "unknown"
]);
export const ContentServiceProfilePrivateSourceProposalFreshnessStatusSchema = z.enum([
  "current",
  "historical",
  "stale",
  "unknown"
]);
export const ContentServiceProfilePrivateSourceProposalAudienceSchema = z.enum([
  "company_wide",
  "department_only",
  "role_restricted",
  "owner_only",
  "unknown"
]);
export const ContentServiceProfilePrivateSourceProposalRetentionDecisionSchema = z.enum([
  "pending_owner_decision",
  "retain_while_source_approved",
  "short_window_only",
  "do_not_retain"
]);

export const PrivateProposalSchema = z.object({
  proposal_id: z.string().trim().min(1),
  source_id: z.string().trim().min(1),
  source_type: z.enum(["private_candidate", "reviewed_internal"]),
  privacy_class: z.enum(["private_local", "redacted_only"]),
  scope: z.enum([
    "service",
    "buyer_problem",
    "cta",
    "claim_policy",
    "evidence_requirement",
    "metric_signal"
  ]),
  target_card_id: z.string().trim().min(1),
  target_card_title: z.string().trim().min(1),
  source_class_label: z.string().trim().min(1),
  source_locator_label: z.string().trim().min(1),
  freshness_status: ContentServiceProfilePrivateSourceProposalFreshnessStatusSchema,
  review_status: ContentServiceProfilePrivateSourceProposalReviewStatusSchema,
  support_level: ContentServiceProfilePrivateSourceProposalSupportLevelSchema,
  risk_tier: ContentServiceProfilePrivateSourceProposalRiskTierSchema,
  data_classes: z.array(z.string().trim().min(1)).nonempty(),
  source_block_refs: z.array(z.string().trim().min(1)).nonempty(),
  retention_decision: ContentServiceProfilePrivateSourceProposalRetentionDecisionSchema,
  deletion_path: z.array(z.string().trim().min(1)).nonempty(),
  eval_case_ids: z.array(z.string().trim().min(1)).nonempty(),
  confidence_label: z.string().trim().min(1),
  owner_role: z.string().trim().min(1),
  audience: ContentServiceProfilePrivateSourceProposalAudienceSchema,
  redacted: z.boolean(),
  blocked_claims: z.array(z.string().trim().min(1)).nonempty(),
  safe_next_step: z.string().trim().min(1),
  promotion_allowed: z.boolean(),
  blocked_write_claim: z.string().trim().min(1)
});
export const ContentServiceProfilePrivateSourceProposalSectionSchema =
  PrivateProposalSchema;

export const ContentServiceProfileNeededSourceTypeSchema = z.enum([
  "public_site_or_reviewed_internal_service_fact",
  "owner_reviewed_source_fact"
]);

export const ContentServiceProfileCoverageGapSchema = z.object({
  gap_id: z.string(),
  area: z.string(),
  severity: z.enum(["blocker", "review_required", "thin", "stale"]),
  label: z.string(),
  reason: z.string(),
  needed_source_type: ContentServiceProfileNeededSourceTypeSchema,
  safe_next_step: z.string(),
  example_work_item_ids: z.array(z.string()).default([])
});

export const ContentServiceProfileReviewRequirementSchema = z.object({
  field: z.string(),
  label: z.string(),
  requirement_type: z.enum(["text", "boolean", "follow_up"]),
  required: z.boolean(),
  blocking_rule: z.string().nullable().optional()
});

export const ContentServiceProfileReviewActionSchema = z.object({
  action_id: z.string(),
  mode: z.enum(["prepare", "review_request"]),
  review_scope: z.enum([
    "general_knowledge_review",
    "public_service_card",
    "coverage_gap",
    "private_service_proposal",
    "private_claim_policy_proposal",
    "private_evidence_policy_proposal"
  ]),
  priority: z.enum(["high", "medium", "low"]),
  decision_options: z.array(z.enum(["approve", "needs_changes", "stale", "reject"])).default([]),
  review_requirements: z.array(ContentServiceProfileReviewRequirementSchema).default([]),
  label: z.string(),
  reason: z.string(),
  blocked_write_claim: z.string(),
  required_human_role: z.string(),
  target_card_id: z.string().nullable().optional(),
  gap_id: z.string().nullable().optional()
});

export const ContentServiceProfileReviewActionSummarySchema = z.object({
  total_count: z.number(),
  review_request_count: z.number(),
  prepare_count: z.number(),
  public_service_review_count: z.number(),
  private_review_count: z.number(),
  private_service_review_count: z.number(),
  private_policy_review_count: z.number(),
  first_review_action_id: z.string().nullable().optional(),
  first_review_action_label: z.string().nullable().optional(),
  first_review_action_reason: z.string().nullable().optional(),
  first_review_action_scope: z
    .enum([
      "general_knowledge_review",
      "public_service_card",
      "coverage_gap",
      "private_service_proposal",
      "private_claim_policy_proposal",
      "private_evidence_policy_proposal"
    ])
    .nullable()
    .optional(),
  first_review_action_priority: z.enum(["high", "medium", "low"]).nullable().optional(),
  first_review_action_target_card_id: z.string().nullable().optional(),
  first_review_action_gap_id: z.string().nullable().optional(),
  first_review_required_fields: z.array(z.string()).default([]),
  first_review_safe_next_step: z.string().nullable().optional(),
  safe_next_step: z.string()
});

export const ContentServiceProfilePrivateReviewValueSchema = z.object({
  proposal_count: z.number(),
  promotion_allowed_count: z.number(),
  blocked_claim_proposal_count: z.number(),
  cta_pattern_proposal_count: z.number(),
  buyer_trigger_proposal_count: z.number(),
  operator_value_score: z.number().min(0).max(10),
  value_summary: z.string(),
  review_value_points: z.array(z.string()).default([]),
  review_questions: z.array(z.string()).default([])
});

export const ContentServiceProfilePrivateReviewQueueItemSchema = z.object({
  proposal_id: z.string(),
  source_id: z.string(),
  scope: z.enum([
    "service",
    "buyer_problem",
    "cta",
    "claim_policy",
    "evidence_requirement",
    "metric_signal"
  ]),
  target_card_id: z.string(),
  target_card_title: z.string(),
  risk_tier: ContentServiceProfilePrivateSourceProposalRiskTierSchema,
  freshness_status: ContentServiceProfilePrivateSourceProposalFreshnessStatusSchema,
  audience: ContentServiceProfilePrivateSourceProposalAudienceSchema,
  review_status: ContentServiceProfilePrivateSourceProposalReviewStatusSchema,
  promotion_allowed: z.boolean(),
  blocked_claim_count: z.number(),
  data_classes: z.array(z.string().trim().min(1)).nonempty(),
  source_block_refs: z.array(z.string().trim().min(1)).nonempty(),
  retention_decision: ContentServiceProfilePrivateSourceProposalRetentionDecisionSchema,
  deletion_path: z.array(z.string().trim().min(1)).nonempty(),
  eval_case_ids: z.array(z.string().trim().min(1)).nonempty(),
  source_locator_label: z.string().trim().min(1),
  owner_role: z.string().trim().min(1),
  redacted: z.boolean(),
  source_trace_ready: z.boolean(),
  safe_next_step: z.string()
});

export const ContentServiceProfileReviewQueueItemSchema = z.object({
  action_id: z.string(),
  review_scope: z.enum([
    "general_knowledge_review",
    "public_service_card",
    "coverage_gap",
    "private_service_proposal",
    "private_claim_policy_proposal",
    "private_evidence_policy_proposal"
  ]),
  priority: z.enum(["high", "medium", "low"]),
  target_card_id: z.string().nullable().optional(),
  target_card_title: z.string(),
  decision_options: z.array(z.enum(["approve", "needs_changes", "stale", "reject"])).default([])
});

export const ContentServiceProfileSourceFactCoverageAuditSchema = z.object({
  pass_state: z.boolean(),
  knowledge_status: ContentKnowledgeLifecycleStatusSchema,
  ready_for_daily_content: z.boolean(),
  production_depth_percent: z.number().min(0).max(100),
  approved_service_percent: z.number().min(0).max(100),
  reviewed_fact_percent: z.number().min(0).max(100),
  fact_count: z.number(),
  fact_review_counts: z.record(z.string(), z.number()).default({}),
  fact_scope_counts: z.record(z.string(), z.number()).default({}),
  fact_connector_counts: z.record(z.string(), z.number()).default({}),
  service_card_count: z.number(),
  coverage_gap_count: z.number(),
  review_action_count: z.number(),
  first_review_action_id: z.string().nullable().optional(),
  first_review_action_label: z.string().nullable().optional(),
  private_proposal_count: z.number(),
  private_review_required_count: z.number(),
  private_review_value: ContentServiceProfilePrivateReviewValueSchema,
  private_review_queue: z.array(ContentServiceProfilePrivateReviewQueueItemSchema).default([]),
  review_action_queue: z.array(ContentServiceProfileReviewQueueItemSchema).default([]),
  blockers: z.array(z.string()).default([]),
  safe_next_step: z.string()
});

export const ContentServiceProfileApprovalReadinessStatusSchema = z.enum([
  "blocked",
  "ready_for_review",
  "ready_for_promotion_request"
]);

export const ContentServiceProfileApprovalReadinessItemSchema = z.object({
  code: z.string(),
  label: z.string(),
  status: ContentServiceProfileApprovalReadinessStatusSchema,
  blocking: z.boolean(),
  detail: z.string(),
  next_step: z.string(),
  related_action_id: z.string().nullable().optional()
});

export const ContentServiceProfileApprovalReadinessSchema = z.object({
  status: ContentServiceProfileApprovalReadinessStatusSchema,
  status_label: z.string(),
  can_request_promotion: z.boolean(),
  mutation_allowed: z.boolean(),
  production_depth_unlocked: z.boolean(),
  reviewed_output_required: z.boolean(),
  approved_current_count: z.number(),
  review_required_count: z.number(),
  first_action_id: z.string().nullable().optional(),
  first_action_label: z.string().nullable().optional(),
  blockers: z.array(z.string()).default([]),
  checklist: z.array(ContentServiceProfileApprovalReadinessItemSchema).default([]),
  safe_next_step: z.string()
});

export const ContentServiceProfileTechnicalTraceSchema = z.object({
  knowledge_card_endpoint: z.string(),
  source_fact_count: z.number(),
  source_fact_ids: z.array(z.string()).default([]),
  private_source_proposal_ids: z.array(z.string()).default([]),
  private_source_protocol_doc: z.string()
});

export const ContentServiceProfileResponseSchema = z.object({
  workspace_id: z.string(),
  workspace_label: z.string(),
  generated_at: z.string(),
  read_only: z.boolean(),
  review_policy: ContentServiceProfileReviewPolicySchema,
  production_depth_readiness: ContentKnowledgeProductionDepthReadinessSchema,
  coverage_summary: ContentServiceProfileCoverageSummarySchema,
  service_sections: z.array(ContentServiceProfileServiceSectionSchema).default([]),
  claim_policy_sections: z.array(ContentServiceProfilePolicySectionSchema).default([]),
  evidence_policy_sections: z.array(ContentServiceProfilePolicySectionSchema).default([]),
  private_source_proposal_summary: ContentServiceProfilePrivateSourceProposalSummarySchema,
  private_review_value: ContentServiceProfilePrivateReviewValueSchema,
  private_source_proposals: z.array(PrivateProposalSchema).default([]),
  coverage_gaps: z.array(ContentServiceProfileCoverageGapSchema).default([]),
  review_action_summary: ContentServiceProfileReviewActionSummarySchema,
  review_actions: z.array(ContentServiceProfileReviewActionSchema).default([]),
  source_fact_coverage: ContentServiceProfileSourceFactCoverageAuditSchema,
  approval_readiness: ContentServiceProfileApprovalReadinessSchema,
  technical_trace: ContentServiceProfileTechnicalTraceSchema
});

export const ContentSalesBriefSchema = z.object({
  id: z.string(),
  work_item_id: z.string(),
  topic: z.string(),
  operations_context: ContentSalesBriefOperationsContextSchema,
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
  knowledge_card_ids: z.array(z.string()).default([]),
  knowledge_constraints: z.array(ContentSalesBriefKnowledgeConstraintSchema).default([]),
  signal_quality: ContentSalesBriefSignalQualitySchema,
  forbidden_claims: z.array(ContentClaimReferenceSchema).default([]),
  missing_evidence: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()),
  source_connectors: z.array(z.string()),
  measurement_plan: z.object({
    measurement_window_id: z.string(),
    metrics_to_watch: z.array(z.string()).default([]),
    baseline_source_connectors: z.array(z.string()).default([]),
    baseline_evidence_ids: z.array(z.string()).default([]),
    measurement_readiness_label: z.string(),
    measurement_readiness_reason: z.string(),
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

export const ContentDraftSectionSchema = z.object({
  heading: z.string(),
  purpose: z.string(),
  evidence_ids: z.array(z.string()).default([]),
  draft_notes: z.array(z.string()).default([])
});

export const ContentDraftEvidenceMapSchema = z.object({
  section_heading: z.string(),
  evidence_ids: z.array(z.string()).default([])
});

export const ContentDraftPackageSchema = z.object({
  id: z.string(),
  work_item_id: z.string(),
  brief_id: z.string(),
  claim_ledger_id: z.string(),
  draft_kind: z.literal("outline"),
  title: z.string(),
  sections: z.array(ContentDraftSectionSchema).default([]),
  section_to_evidence_map: z.array(ContentDraftEvidenceMapSchema).default([]),
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

export const ContentWorkItemPreflightRequestSchema = z.object({
  item: ContentWorkItemSchema,
  inventory_records: z.array(ContentInventoryRecordSchema).default([]),
  duplicate_risk: ContentInventoryDuplicateRiskSchema.default("unknown")
});

const ContentWorkItemBriefRequestFields = {
  item: ContentWorkItemSchema,
  inventory_records: z.array(ContentInventoryRecordSchema).default([]),
  duplicate_risk: ContentInventoryDuplicateRiskSchema.default("unknown"),
  claim_ledger: ContentClaimLedgerSchema,
  seed: ContentSalesBriefSeedSchema,
  enrichment: z.lazy(() => ContentOpportunityEnrichmentSchema).nullable().optional(),
  knowledge_match: ContentKnowledgeCardMatchSchema.nullable().optional()
};

export const ContentWorkItemSalesBriefRequestSchema = z.object({
  ...ContentWorkItemBriefRequestFields
});

export const ContentWorkItemDraftPackageRequestSchema = z.object({
  ...ContentWorkItemBriefRequestFields,
  sales_brief: ContentSalesBriefSchema.nullable().optional()
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

export const ContentStructuredGenerationBrowserReadinessSchema = z
  .object({
    status: z.enum(["ready", "blocked"]),
    editable_section_headings: z
      .array(z.string().refine((value) => value.trim().length > 0))
      .default([]),
    blockers: z.array(ContentWorkflowBlockerSchema).default([]),
    safe_next_step: z.string(),
    publish_ready: z.literal(false)
  })
  .superRefine((readiness, context) => {
    if (
      readiness.status === "ready" &&
      (readiness.editable_section_headings.length === 0 || readiness.blockers.length > 0)
    ) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["status"],
        message: "ready browser generation state requires headings and no blockers"
      });
    }
    if (
      readiness.status === "blocked" &&
      (readiness.editable_section_headings.length > 0 || readiness.blockers.length === 0)
    ) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["status"],
        message: "blocked browser generation state requires blockers and no headings"
      });
    }
  });

export const ContentQualityDimensionSchema = z.object({
  status: z.enum(["pass", "needs_changes", "blocked"]),
  label: z.string(),
  reason: z.string()
});

export const ContentQualityFindingCodeSchema = z.enum([
  "missing_draft_package",
  "draft_package_mismatch",
  "draft_package_marked_publish_ready",
  "missing_structured_output",
  "section_missing_evidence",
  "unknown_evidence_reference",
  "missing_claim_ledger",
  "claim_ledger_blocks_quality",
  "unsupported_claim_used",
  "forbidden_claim_used",
  "claim_missing_required_evidence",
  "required_claim_missing",
  "missing_forbidden_claim_acknowledgement",
  "duplicate_risk_not_clear",
  "missing_measurement_window",
  "sales_brief_signal_review_required",
  "sales_brief_signal_thin",
  "weak_cta",
  "missing_service_fit",
  "missing_search_intent",
  "missing_buyer_problem",
  "missing_internal_links",
  "non_polish_language"
]);

export const ContentQualityFindingSchema = z.object({
  code: ContentQualityFindingCodeSchema,
  severity: z.enum(["blocker", "needs_changes", "info"]),
  label: z.string(),
  reason: z.string(),
  next_step: z.string(),
  affected_section: z.string().nullable().optional(),
  ...ContentEvidenceTraceFields
});

export const ContentRevisionInstructionSchema = z.object({
  id: z.string(),
  affected_section: z.string().nullable().optional(),
  change: z.string(),
  reason: z.string(),
  required_evidence_ids: z.array(z.string()).default([]),
  forbidden_claims_to_avoid: z.array(z.string()).default([]),
  human_review_checklist_additions: z.array(z.string()).default([])
});

export const ContentQualityReviewSchema = z.object({
  review_id: z.string(),
  work_item_id: z.string(),
  draft_package_id: z.string().nullable().optional(),
  verdict: z.enum(["blocked", "needs_changes", "reviewable", "ready_for_human_review"]),
  evidence_coverage: ContentQualityDimensionSchema,
  claim_safety: ContentQualityDimensionSchema,
  duplicate_risk: ContentQualityDimensionSchema,
  usefulness: ContentQualityDimensionSchema,
  service_fit: ContentQualityDimensionSchema,
  search_intent_fit: ContentQualityDimensionSchema,
  buyer_problem_fit: ContentQualityDimensionSchema,
  cta_quality: ContentQualityDimensionSchema,
  factual_precision: ContentQualityDimensionSchema,
  polish_language_quality: ContentQualityDimensionSchema,
  internal_link_fit: ContentQualityDimensionSchema,
  measurement_readiness: ContentQualityDimensionSchema,
  blockers: z.array(ContentQualityFindingSchema).default([]),
  findings: z.array(ContentQualityFindingSchema).default([]),
  revision_instructions: z.array(ContentRevisionInstructionSchema).default([]),
  ...ContentEvidenceTraceFields,
  ...ContentSafeNextStepField
});

export const ContentWorkItemQualityReviewRequestSchema = z.object({
  item: ContentWorkItemSchema,
  draft_package: ContentDraftPackageSchema.nullable().optional(),
  structured_output: StructuredDraftOutputSchema.nullable().optional(),
  claim_ledger: ContentClaimLedgerSchema.nullable().optional(),
  sales_brief: ContentSalesBriefSchema.nullable().optional(),
  duplicate_risk: ContentInventoryDuplicateRiskSchema.default("clear")
});

export const ContentWorkItemQualityReviewResponseSchema = z.object({
  item: ContentWorkItemSchema,
  quality_review: ContentQualityReviewSchema
});

export const ContentRevisionPlanBlockerSchema = ContentBlockerBaseSchema;

export const ContentRevisionPlanSchema = z.object({
  id: z.string(),
  work_item_id: z.string(),
  quality_review_id: z.string().nullable().optional(),
  status: z.enum(["blocked", "ready", "no_changes_needed"]),
  draft_revision_allowed: z.boolean(),
  instructions: z.array(ContentRevisionInstructionSchema).default([]),
  blockers: z.array(ContentRevisionPlanBlockerSchema).default([]),
  ...ContentEvidenceTraceFields,
  ...ContentSafeNextStepField
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
  review_recordable: z.boolean(),
  review_recorded: z.boolean(),
  wordpress_handoff_allowed: z.boolean()
});

export const ContentWorkItemHumanReviewRequestSchema = z.object({
  item: ContentWorkItemSchema,
  review: ContentHumanReviewSchema.nullable().optional(),
  draft_package: ContentDraftPackageSchema.nullable().optional(),
  claim_ledger: ContentClaimLedgerSchema.nullable().optional()
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

export const ContentDraftRevisionSectionSchema = z.object({
  section_id: z.string().min(1).nullable().optional(),
  heading: z.string().refine((value) => value.trim().length > 0),
  body_markdown: z.string().refine((value) => value.trim().length > 0),
  content_html: z.string().refine((value) => value.trim().length > 0).nullable().optional(),
  query_terms: z.array(z.string().refine((value) => value.trim().length > 0)).default([]),
  evidence_ids: z.array(z.string().refine((value) => value.trim().length > 0)).default([]),
  claim_ids: z.array(z.string().refine((value) => value.trim().length > 0)).default([]),
  source_material_ids: z.array(z.string().refine((value) => value.trim().length > 0)).default([]),
  knowledge_card_ids: z.array(z.string().refine((value) => value.trim().length > 0)).default([])
});

export const ContentWordPressDraftHandoffSchema = z.object({
  id: z.string(),
  work_item_id: z.string(),
  draft_package_id: z.string(),
  human_review_id: z.string().nullable().optional(),
  audit_id: z.string().nullable().optional(),
  connector: z.literal("wordpress_ekologus"),
  operation_type: z.literal("create_wordpress_draft"),
  status: z.literal("prepared"),
  post_status: z.literal("draft"),
  authoring_mode: z.enum(["the_content", "acf_flexible_content", "unknown"]).default("unknown"),
  title: z.string(),
  final_canonical_url: z.string(),
  intended_final_url: z.string().nullable().optional(),
  preview_url: z.string().nullable().optional(),
  evidence_ids: z.array(z.string()).default([]),
  revision_binding: ContentDraftRevisionBindingSchema.nullable().optional(),
  revision_sections: z.array(ContentDraftRevisionSectionSchema).default([]),
  revision_document: z.lazy(() => ContentDraftRevisionSchema).nullable().optional(),
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

export const ContentWorkItemWordPressDraftHandoffRequestSchema = z.object({
  item: ContentWorkItemSchema,
  draft_package: ContentDraftPackageSchema.nullable().optional(),
  human_review: ContentHumanReviewSchema.nullable().optional(),
  audit: ContentWordPressDraftAuditEnvelopeSchema.nullable().optional()
});

export const ContentWordPressDraftExecutionPayloadSchema = z.object({
  connector: z.literal("wordpress_ekologus"),
  endpoint_kind: z.literal("posts"),
  post_status: z.literal("draft"),
  title: z.string(),
  content_markdown: z.string(),
  content_html: z.string().nullable().optional(),
  authoring_mode: z.enum(["the_content", "acf_flexible_content", "unknown"]).default("unknown"),
  meta_title: z.string().nullable().optional(),
  meta_description: z.string().nullable().optional(),
  meta_write_status: z.enum(["not_present", "review_required", "mapped"])
    .default("not_present"),
  metadata_blockers: z.array(z.object({
    code: z.literal("missing_wordpress_meta_mapping"),
    label: z.string(),
    reason: z.string(),
    next_step: z.string()
  })).optional(),
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

export const ContentWordPressDraftExecutionBoundarySchema = z.object({
  allowed_operation: z.literal("create_wordpress_draft"),
  dry_run_default: z.boolean(),
  live_write_enabled: z.boolean(),
  live_adapter_configured: z.boolean(),
  publish_allowed: z.literal(false),
  destructive_update_allowed: z.literal(false)
});

export const ContentWordPressDraftWriteAuthorizationSchema = z.object({
  action_id: z.string(),
  preview_audit_id: z.string(),
  review_audit_id: z.string(),
  confirmation_audit_id: z.string(),
  impact_audit_id: z.string().nullable().optional(),
  apply_audit_id: z.string().nullable().optional(),
  confirmed_by: z.string(),
  wordpress_draft_binding: ContentDraftRevisionBindingSchema.nullable().optional()
});

export const ContentWordPressDraftSectionOverrideSchema = z.object({
  heading: z.string(),
  body_markdown: z.string(),
  evidence_ids: z.array(z.string()).default([])
});

export const ContentWordPressDraftWriteReadinessRequirementSchema = z.object({
  event_type: z.string(),
  label: z.string(),
  satisfied: z.boolean().default(false),
  audit_event_id: z.string().nullable().optional(),
  actor: z.string().nullable().optional()
});

export const ContentWordPressDraftWriteReadinessBlockerSchema = z.object({
  code: z.string(),
  label: z.string(),
  reason: z.string(),
  next_step: z.string()
});

export const ContentWordPressDraftWriteReadinessResponseSchema = z.object({
  response_type: z.literal("wordpress_draft_write_readiness"),
  contract: z.literal("wordpress_draft_write_readiness_v1"),
  connector: z.string(),
  action_id: z.string(),
  ready: z.boolean(),
  live_write_enabled_by_env: z.boolean(),
  rest_adapter_configured: z.boolean(),
  publish_allowed: z.literal(false),
  destructive_update_allowed: z.literal(false),
  required_audit_events: z.array(ContentWordPressDraftWriteReadinessRequirementSchema).default([]),
  missing_audit_event_types: z.array(z.string()).default([]),
  write_authorization_status: z
    .enum([
      "missing_audit_trace",
      "audit_actor_mismatch",
      "available",
      "blocked_outside_action_apply"
    ])
    .default("missing_audit_trace"),
  suggested_write_authorization: ContentWordPressDraftWriteAuthorizationSchema.nullable().optional(),
  blockers: z.array(ContentWordPressDraftWriteReadinessBlockerSchema).default([]),
  operator_next_step: z.string(),
  evidence_ids: z.array(z.string()).default([]),
  source_connectors: z.array(z.string()).default([])
});

export const ContentWordPressExistingDraftUpdateReadinessResponseSchema = z.object({
  response_type: z.literal("wordpress_existing_draft_update_readiness"),
  contract: z.literal("wordpress_existing_draft_update_readiness_v1"),
  connector: z.string(),
  action_id: z.string(),
  work_item_id: z.string(),
  target_post_id: z.string().nullable().optional(),
  target_url: z.string().nullable().optional(),
  current_state_available: z.boolean(),
  current_section_count: z.number().int().nonnegative(),
  proposed_section_count: z.number().int().nonnegative(),
  section_diff_preview: z.array(z.object({
    heading: z.string(),
    current_summary: z.string().default(""),
    proposed_summary: z.string().default(""),
    status: z.enum(["unchanged", "changed", "proposed", "missing_current"])
  })).default([]),
  ready: z.boolean(),
  update_supported: z.boolean(),
  publish_allowed: z.literal(false),
  destructive_update_allowed: z.literal(false),
  blockers: z.array(ContentWordPressDraftWriteReadinessBlockerSchema).default([]),
  operator_next_step: z.string(),
  evidence_ids: z.array(z.string()).default([]),
  source_connectors: z.array(z.string()).default([])
});

export const ContentWordPressDraftExecutionResultSchema = z.object({
  status: z.enum(["dry_run_ready", "created", "blocked"]),
  mode: z.enum(["dry_run", "live"]),
  boundary: ContentWordPressDraftExecutionBoundarySchema,
  payload: ContentWordPressDraftExecutionPayloadSchema.nullable().optional(),
  revision_binding: ContentDraftRevisionBindingSchema.nullable().optional(),
  wordpress_post_id: z.string().nullable().optional(),
  external_write_attempted: z.boolean(),
  blockers: z.array(ContentWordPressDraftExecutionBlockerSchema).default([])
});

export const ContentWordPressDraftReadbackBlockerSchema = z.object({
  code: z.enum([
    "missing_wordpress_post_id",
    "wordpress_draft_read_failed",
    "wordpress_draft_status_mismatch",
    "wordpress_draft_content_mismatch",
    "wordpress_draft_acf_mismatch",
    "wordpress_draft_verification_unavailable"
  ]),
  label: z.string(),
  reason: z.string(),
  next_step: z.string()
});

export const ContentWordPressDraftReadbackSchema = z.object({
  status: z.enum(["available", "blocked"]),
  connector: z.string().default("wordpress_ekologus"),
  wordpress_post_id: z.string().nullable().optional(),
  post_status: z.string(),
  title: z.string(),
  link: z.string(),
  edit_link: z.string().optional(),
  modified_gmt: z.string(),
  content_summary: z.string(),
  content_word_count: z.number().nullable().optional(),
  acf_field_count: z.number().nullable().optional(),
  acf_field_names: z.array(z.string()).default([]),
  content_digest: z.string(),
  expected_content_digest: z.string().nullable().optional(),
  acf_digest: z.string(),
  expected_acf_digest: z.string().nullable().optional(),
  verification_status: z.enum(["verified", "blocked"]),
  blockers: z.array(ContentWordPressDraftReadbackBlockerSchema).default([])
});

export const ContentWordPressDraftActivationPacketResponseSchema = z.object({
  response_type: z.literal("wordpress_draft_activation_packet"),
  contract: z.literal("wordpress_draft_activation_packet_v1"),
  action_id: z.string(),
  work_item_id: z.string(),
  topic: z.string(),
  final_canonical_url: z.string().nullable().optional(),
  draft_package_ready: z.boolean(),
  draft_package_id: z.string().nullable().optional(),
  review_preview_ready: z.boolean(),
  review_preview_status_label: z.string(),
  human_review_checklist: z.array(z.string()).default([]),
  human_review_ready: z.boolean(),
  audit_ready: z.boolean(),
  handoff_ready: z.boolean(),
  handoff_id: z.string().nullable().optional(),
  dry_run_ready: z.boolean(),
  live_write_enabled_by_env: z.boolean(),
  publish_allowed: z.literal(false),
  destructive_update_allowed: z.literal(false),
  external_write_attempted: z.literal(false),
  handoff_blockers: z.array(z.string()).default([]),
  execution_blockers: z.array(z.string()).default([]),
  activation_missing_step: z.enum([
    "draft_package",
    "human_review",
    "audit",
    "handoff",
    "dry_run",
    "ready"
  ]),
  activation_missing_step_label: z.string(),
  activation_missing_readiness_labels: z.array(z.string()).default([]),
  execution_result: ContentWordPressDraftExecutionResultSchema,
  draft_readback: ContentWordPressDraftReadbackSchema.nullable().optional(),
  operator_next_step: z.string(),
  next_steps: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()).default([]),
  source_connectors: z.array(z.string()).default([])
});

export const ContentWorkItemWordPressDraftExecutionRequestSchema = z.object({
  handoff: ContentWordPressDraftHandoffSchema.nullable().optional(),
  draft_package: ContentDraftPackageSchema.nullable().optional(),
  mode: z.literal("dry_run").default("dry_run"),
  write_authorization: ContentWordPressDraftWriteAuthorizationSchema.nullable().optional(),
  section_overrides: z.array(ContentWordPressDraftSectionOverrideSchema).default([])
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
  deployment_id: z.string().nullable().optional(),
  deployed_revision_id: z.string().nullable().optional(),
  deployed_revision_digest: z.string().nullable().optional(),
  success_claim_allowed: z.boolean()
});

export const ContentMeasurementWindowBuildResultSchema = z.object({
  window: ContentMeasurementWindowSchema.nullable().optional(),
  blockers: z.array(ContentWorkflowBlockerSchema).default([])
});

export const ContentPublicDeploymentSchema = z.object({
  deployment_id: z.string(),
  work_item_id: z.string(),
  revision_id: z.string(),
  revision_digest: z.string(),
  public_url: z.string(),
  wordpress_post_id: z.string(),
  publication_evidence_id: z.string(),
  publication_source_connector: z.string(),
  observed_at: z.string(),
  confirmed_by: z.string(),
  confirmed_at: z.string()
});

export const ContentPublicDeploymentConfirmationResponseSchema = z.object({
  deployment: ContentPublicDeploymentSchema
});

export const ContentPublicDeploymentConfirmationCommandSchema = z.object({
  expected_revision_digest: z.string().regex(/^[0-9a-f]{64}$/),
  wordpress_post_id: z.string().min(1),
  publication_evidence_id: z.string().min(1),
  confirmed_by: z.string().min(1).max(200)
});

export const ContentPublicDeploymentObservationSchema = z.object({
  wordpress_post_id: z.string(),
  publication_evidence_id: z.string(),
  publication_source_connector: z.string(),
  public_url: z.string(),
  observed_at: z.string()
});

export const ContentPublicDeploymentReadResponseSchema = z.object({
  deployment: ContentPublicDeploymentSchema.nullable().optional(),
  publication_observations: z.array(ContentPublicDeploymentObservationSchema).default([]),
  measurement_window: ContentMeasurementWindowSchema.nullable().optional(),
  measurement_outcome: z.lazy(() => ContentMeasurementOutcomeInterpretationSchema).nullable().optional(),
  learning_proposal: z.lazy(() => ContentLearningProposalSchema).nullable().optional(),
  outcome_allowed: z.boolean().default(false),
  safe_next_step: z.string()
});

export const ContentMeasurementObservedMetricSchema = z.object({
  metric: z.string(),
  baseline_value: z.number().nullable().optional(),
  observation_value: z.number().nullable().optional(),
  source_connector: z.string(),
  evidence_ids: z.array(z.string()).default([]),
  metric_fact_ids: z.array(z.string()).default([]),
  refresh_run_ids: z.array(z.string()).default([]),
  work_item_id: z.string().nullable().optional(),
  measurement_window_id: z.string().nullable().optional(),
  content_url: z.string().nullable().optional(),
  quality_state: z.enum(["verified", "partial", "unverified", "unknown"]).optional(),
  settlement_state: z.enum(["settled", "settling", "not_applicable", "unknown"]).optional(),
  freshness_state: z.enum(["fresh", "stale", "unknown"]).optional(),
  interpretation_caveats: z.array(z.string()).default([])
});

export const ContentMeasurementOutcomeInterpretationSchema = z.object({
  id: z.string(),
  work_item_id: z.string(),
  measurement_window_id: z.string(),
  deployment_id: z.string().nullable().optional(),
  deployed_revision_id: z.string().nullable().optional(),
  deployed_revision_digest: z.string().nullable().optional(),
  status: z.enum([
    "not_ready",
    "insufficient_data",
    "noisy_inconclusive",
    "directional_improvement",
    "likely_underperformance",
    "measured_success"
  ]),
  status_label: z.string(),
  conclusion: z.string(),
  confidence: z.enum(["none", "low", "medium", "high"]),
  evidence_ids: z.array(z.string()).default([]),
  source_connectors: z.array(z.string()).default([]),
  metric_fact_ids: z.array(z.string()).default([]),
  refresh_run_ids: z.array(z.string()).default([]),
  limitations: z.array(z.string()).default([]),
  observed_metrics: z.array(ContentMeasurementObservedMetricSchema).default([]),
  success_claim_allowed: z.boolean(),
  queue_feedback_allowed: z.boolean(),
  safe_next_step: z.string()
});

export const ContentWorkItemMeasurementWindowResponseSchema = z.object({
  item: ContentWorkItemSchema,
  updated_item: ContentWorkItemSchema,
  measurement_window_result: ContentMeasurementWindowBuildResultSchema,
  outcome_blockers: z.array(ContentWorkflowBlockerSchema).default([])
});

export const ContentWorkItemMeasurementWindowRequestSchema = z.object({
  work_item_id: z.string().min(1),
  revision_id: z.string().min(1)
});

export const ContentWorkItemMeasurementOutcomeRequestSchema = z.object({
  work_item_id: z.string().min(1),
  measurement_window_id: z.string().min(1)
});

export const ContentWorkItemMeasurementOutcomeResponseSchema = z.object({
  outcome: ContentMeasurementOutcomeInterpretationSchema
});

export const ContentLearningProposalSchema = z.object({
  id: z.string(),
  work_item_id: z.string(),
  measurement_window_id: z.string(),
  measurement_outcome_id: z.string(),
  verdict: z.enum([
    "noisy_inconclusive",
    "directional_improvement",
    "likely_underperformance",
    "measured_success"
  ]),
  review_status: z.literal("review_required"),
  decision_summary: z.string(),
  proposed_learning: z.string(),
  evidence_ids: z.array(z.string()).default([]),
  source_connectors: z.array(z.string()).default([]),
  metric_fact_ids: z.array(z.string()).default([]),
  refresh_run_ids: z.array(z.string()).default([]),
  limitations: z.array(z.string()).default([]),
  human_acceptance_required: z.literal(true),
  knowledge_update_allowed: z.literal(false),
  queue_update_allowed: z.literal(false),
  success_claim_allowed: z.literal(false)
});

export const ContentWorkItemLearningProposalRequestSchema = z.object({
  work_item_id: z.string().min(1),
  measurement_window_id: z.string().min(1)
});

export const ContentWorkItemLearningProposalResponseSchema = z.object({
  proposal: ContentLearningProposalSchema
});

const CONTENT_WORKFLOW_OPERATOR_STEP_ORDER = [
  "scope",
  "section_map",
  "draft",
  "review",
  "dev_draft"
] as const;

export const ContentDraftRevisionProposalSectionLineageSchema = z.object({
  heading: z.string().refine((value) => value.trim().length > 0),
  evidence_ids: z.array(z.string()).default([]),
  claim_ids: z.array(z.string()).default([]),
  source_material_ids: z.array(z.string()).default([]),
  knowledge_card_ids: z.array(z.string()).default([])
});

export const ContentDraftRevisionProposalCtaLineageSchema = z.object({
  cta_id: z.string().refine((value) => value.trim().length > 0),
  evidence_ids: z.array(z.string().refine((value) => value.trim().length > 0)).min(1),
  claim_ids: z.array(z.string().refine((value) => value.trim().length > 0)).default([])
});

export const ContentDraftRevisionProposalMetadataSchema = z
  .object({
    source: z.literal("codex_app_server"),
    codex_run_id: z.string().refine((value) => value.trim().length > 0),
    selected_section_headings: z
      .array(z.string().refine((value) => value.trim().length > 0))
      .default([]),
    section_lineage: z.array(ContentDraftRevisionProposalSectionLineageSchema).default([]),
    selected_cta_ids: z.array(z.string().refine((value) => value.trim().length > 0)).default([]),
    cta_lineage: z.array(ContentDraftRevisionProposalCtaLineageSchema).default([]),
    quality_verdict: z.enum(["needs_changes", "reviewable", "ready_for_human_review"]),
    quality_finding_codes: z.array(z.string()).default([]),
    regulatory_assurance_run_id: z.string().trim().min(1).nullable().optional(),
    regulatory_assurance_criteria_version: z.string().trim().min(1).nullable().optional(),
    review_scope: z.enum([
      "persisted_selected_sections_and_declared_lineage",
      "persisted_selected_components_and_declared_lineage",
      "persisted_full_document_and_declared_lineage"
    ]),
    semantic_review_required: z.literal(true)
  })
  .superRefine((metadata, context) => {
    const headings = metadata.selected_section_headings;
    const lineageHeadings = metadata.section_lineage.map((lineage) => lineage.heading);
    const ctaIds = metadata.selected_cta_ids;
    const lineageCtaIds = metadata.cta_lineage.map((lineage) => lineage.cta_id);
    const sectionSelection = headings.length > 0;
    const ctaSelection = ctaIds.length > 0;
    const assuranceBound =
      metadata.regulatory_assurance_run_id != null ||
      metadata.regulatory_assurance_criteria_version != null;
    if (
      assuranceBound &&
      (!metadata.regulatory_assurance_run_id ||
        !metadata.regulatory_assurance_criteria_version)
    ) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["regulatory_assurance_run_id"],
        message: "regulatory assurance provenance must be complete"
      });
    }
    const validSections =
      new Set(headings).size === headings.length &&
      headings.length === lineageHeadings.length &&
      headings.every((heading, index) => heading === lineageHeadings[index]) &&
      metadata.cta_lineage.length === 0 &&
      ctaIds.length === 0;
    const validCta =
      ctaIds.length === 1 &&
      ctaIds[0] === lineageCtaIds[0] &&
      lineageCtaIds.length === 1 &&
      metadata.section_lineage.length === 0 &&
      headings.length === 0 &&
      metadata.review_scope === "persisted_selected_components_and_declared_lineage";
    if (sectionSelection === ctaSelection || !(validSections || validCta)) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["selected_section_headings"],
        message: "proposal lineage must match exactly one selected component kind"
      });
    }
  });

export const ContentDraftRevisionPageAssetsSchema = z.object({
  wordpress_title: z.string().min(1),
  meta_title: z.string().min(1),
  meta_description: z.string().min(1),
  h1: z.string().min(1),
  lead: z.string().min(1)
});

export const ContentDraftRevisionFaqItemSchema = z.object({
  faq_id: z.string().min(1),
  question: z.string().min(1),
  answer_markdown: z.string().min(1),
  query_terms: z.array(z.string().refine((value) => value.trim().length > 0)).default([]),
  evidence_ids: z.array(z.string().refine((value) => value.trim().length > 0)).min(1),
  claim_ids: z.array(z.string().refine((value) => value.trim().length > 0)).default([])
});

export const ContentDraftRevisionCtaBlockSchema = z.object({
  cta_id: z.string().min(1),
  placement: z.string().min(1),
  body_markdown: z.string().min(1),
  evidence_ids: z.array(z.string().refine((value) => value.trim().length > 0)).min(1),
  claim_ids: z.array(z.string().refine((value) => value.trim().length > 0)).default([])
});

const containsInlineLink = (value: string): boolean => {
  const folded = value.toLowerCase();
  return (
    folded.includes("http://") ||
    folded.includes("https://") ||
    folded.includes("mailto:") ||
    folded.includes("javascript:") ||
    folded.includes("href=") ||
    folded.includes("href =") ||
    ["[", "]", "<", ">"].some((character) => value.includes(character)) ||
    value.includes("//")
  );
};

const isSafePublicContentUrl = (value: string): boolean => {
  const containsControlCharacter = Array.from(value).some((character) => {
    const code = character.charCodeAt(0);
    return code <= 0x20 || code === 0x7f;
  });
  if (
    value !== value.trim() ||
    containsControlCharacter ||
    /[<>"'`(){}|\\^]/.test(value) ||
    value.includes("[") ||
    value.includes("]")
  ) return false;
  try {
    const parsed = new URL(value);
    return (
      parsed.protocol === "https:" &&
      ["ekologus.pl", "www.ekologus.pl", "sklep.ekologus.pl"].includes(
        parsed.hostname.toLowerCase()
      ) &&
      parsed.username === "" &&
      parsed.password === "" &&
      parsed.port === "" &&
      parsed.search === "" &&
      parsed.hash === "" &&
      parsed.pathname.startsWith("/")
    );
  } catch {
    return false;
  }
};

export const ContentDraftRevisionSourceProvenanceSchema = z.object({
  source_fact_id: z.string().min(1),
  source_url_or_path: z.string().min(1),
  freshness_date: z.string().min(1),
  reviewer: z.string().min(1).nullable().optional(),
  evidence_ids: z.array(z.string().min(1)).min(1)
});

export const ContentDraftRevisionInternalLinkSchema = z.object({
  link_id: z.string().min(1),
  placement: z.string().min(1),
  target_url: z.string().min(1),
  anchor_text: z.string().min(1),
  evidence_ids: z.array(z.string().refine((value) => value.trim().length > 0)).min(1),
  claim_ids: z.array(z.string().refine((value) => value.trim().length > 0)).default([])
});

const isSafeOfficialSourceUrl = (value: string): boolean => {
  const containsControlCharacter = Array.from(value).some((character) => {
    const code = character.charCodeAt(0);
    return code <= 0x20 || code === 0x7f;
  });
  if (
    value !== value.trim() ||
    containsControlCharacter ||
    /[<>"'`(){}|\\^]/.test(value) ||
    value.includes("[") ||
    value.includes("]")
  ) return false;
  try {
    const parsed = new URL(value);
    return (
      parsed.protocol === "https:" &&
      parsed.hostname.length > 0 &&
      parsed.username === "" &&
      parsed.password === ""
    );
  } catch {
    return false;
  }
};

const isIsoDate = (value: string): boolean => {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  return !Number.isNaN(Date.parse(`${value}T00:00:00Z`));
};

export const ContentDraftRevisionOfficialSourceReferenceSchema = z.object({
  source_fact_id: z.string().trim().min(1),
  source_url: z.string().trim().min(1).refine(isSafeOfficialSourceUrl),
  source_title: z.string().trim().min(1),
  verified_on: z.string().trim().min(1).refine(isIsoDate),
  evidence_ids: z.array(z.string().trim().min(1)).min(1),
  regulatory_requirement_ids: z.array(z.string().trim().min(1)).min(1)
});

export const ContentDraftRevisionSchema = z.object({
  schema_version: z
    .enum(["wilq_content_draft_revision_v1", "wilq_content_draft_revision_v2"])
    .default("wilq_content_draft_revision_v1"),
  revision_id: z.string(),
  work_item_id: z.string(),
  revision_number: z.number().int().positive(),
  base_revision_id: z.string().nullable(),
  content_digest: z.string().regex(/^[0-9a-f]{64}$/),
  draft_package_id: z.string(),
  draft_package_digest: z.string().regex(/^[0-9a-f]{64}$/),
  planning_digest: z.string().regex(/^[0-9a-f]{64}$/).nullable().optional(),
  planning_input_digest: z.string().regex(/^[0-9a-f]{64}$/).nullable().optional(),
  service_card_id: z.string().min(1).nullable().optional(),
  service_digest: z.string().regex(/^[0-9a-f]{64}$/).nullable().optional(),
  inventory_digest: z.string().regex(/^[0-9a-f]{64}$/).nullable().optional(),
  source_material_ids: z.array(z.string()).default([]),
  knowledge_card_ids: z.array(z.string()).default([]),
  document_kind: z.enum(["refresh_existing", "new_page"]).default("refresh_existing"),
  final_canonical_url: z.string().nullable().default(null),
  new_page_document_identity: ContentNewPageDocumentIdentitySchema.nullable().optional(),
  source_provenance: z.array(ContentDraftRevisionSourceProvenanceSchema).optional(),
  title: z.string().refine((value) => value.trim().length > 0),
  page_assets: ContentDraftRevisionPageAssetsSchema.nullable().optional(),
  sections: z.array(ContentDraftRevisionSectionSchema).min(1),
  faq: z.array(ContentDraftRevisionFaqItemSchema).default([]),
  cta_blocks: z.array(ContentDraftRevisionCtaBlockSchema).default([]),
  internal_links: z.array(ContentDraftRevisionInternalLinkSchema).default([]),
  official_source_references: z.array(ContentDraftRevisionOfficialSourceReferenceSchema).default([]),
  proposal_metadata: ContentDraftRevisionProposalMetadataSchema.nullable().optional(),
  correction_reason: z.enum(["canonical_html_alignment", "official_source_lineage_rebase"]).nullable().optional(),
  publish_ready: z.literal(false),
  created_by: z.string().refine((value) => value.trim().length > 0),
  created_at: z.string()
}).superRefine((revision, context) => {
  if (revision.schema_version === "wilq_content_draft_revision_v1") {
    if (
      revision.document_kind !== "refresh_existing" ||
      !revision.final_canonical_url?.trim() ||
      revision.new_page_document_identity ||
      revision.official_source_references.length > 0
    ) {
      context.addIssue({ code: z.ZodIssueCode.custom, message: "Historical v1 revision requires a refresh URL and cannot carry new-page identity or official source references." });
    }
    return;
  }
  const sourceFactIds = revision.official_source_references.map((item) => item.source_fact_id);
  if (sourceFactIds.length !== new Set(sourceFactIds).size) {
    context.addIssue({ code: z.ZodIssueCode.custom, path: ["official_source_references"], message: "Full-document official source references require unique source fact IDs." });
  }
  if (revision.document_kind === "refresh_existing" && (!revision.final_canonical_url?.trim() || revision.new_page_document_identity)) {
    context.addIssue({ code: z.ZodIssueCode.custom, path: ["final_canonical_url"], message: "Refresh revision requires a public canonical URL and no new-page identity." });
  }
  if (revision.document_kind === "new_page" && (
    revision.final_canonical_url !== null ||
    !revision.new_page_document_identity ||
    revision.new_page_document_identity.work_item_id !== revision.work_item_id ||
    revision.service_card_id !== revision.new_page_document_identity.service_card_id ||
    revision.service_digest !== revision.new_page_document_identity.service_card_digest
  )) {
    context.addIssue({ code: z.ZodIssueCode.custom, path: ["new_page_document_identity"], message: "New-page revision requires exact pre-document identity and no public URL." });
  }
  const requiredBindings = [
    revision.planning_input_digest,
    revision.service_card_id,
    revision.service_digest,
    revision.inventory_digest,
    revision.page_assets
  ];
  if (requiredBindings.some((value) => value == null)) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["schema_version"],
      message: "full-document revision requires exact bindings and page assets"
    });
  }
  if (revision.page_assets?.wordpress_title !== revision.title) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["page_assets", "wordpress_title"],
      message: "WordPress title must match the revision title"
    });
  }
  const sectionIds = revision.sections.map((section) => section.section_id);
  if (sectionIds.some((value) => !value) || new Set(sectionIds).size !== sectionIds.length) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["sections"],
      message: "full-document sections require unique stable IDs"
    });
  }
  if (revision.sections.some((section) => section.evidence_ids.length === 0)) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["sections"],
      message: "full-document sections require evidence lineage"
    });
  }
  const stableIds: Array<[string[], Array<string | number>, string]> = [
    [revision.faq.map((item) => item.faq_id), ["faq"], "FAQ IDs must be unique"],
    [revision.cta_blocks.map((item) => item.cta_id), ["cta_blocks"], "CTA IDs must be unique"],
    [revision.internal_links.map((item) => item.link_id), ["internal_links"], "link IDs must be unique"]
  ];
  for (const [values, path, message] of stableIds) {
    if (new Set(values).size !== values.length) {
      context.addIssue({ code: z.ZodIssueCode.custom, path, message });
    }
  }
  const allowedPlacements = new Set(["after_lead", "after_content", ...sectionIds]);
  const placements = [
    ...revision.cta_blocks.map((item) => item.placement),
    ...revision.internal_links.map((item) => item.placement)
  ];
  if (placements.some((placement) => !allowedPlacements.has(placement))) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["internal_links"],
      message: "CTA and link placements must target the document structure"
    });
  }
  revision.internal_links.forEach((link, index) => {
    const anchor = link.anchor_text.trim();
    if (
      ["[", "]", "<", ">", "\\", "\r", "\n", "\t"].some((character) =>
        anchor.includes(character)
      ) ||
      anchor.includes("://") ||
      /^(mailto|javascript):/i.test(anchor)
    ) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["internal_links", index, "anchor_text"],
        message: "internal-link anchor text must be plain text"
      });
    }
    if (!isSafePublicContentUrl(link.target_url)) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["internal_links", index, "target_url"],
        message: "internal links must target a safe public Ekologus URL"
      });
    }
  });
  const generatedText: Array<[string, Array<string | number>]> = [
    [revision.title, ["title"]],
    ...Object.entries(revision.page_assets ?? {}).map(([field, value]) => [
      value,
      ["page_assets", field]
    ] as [string, Array<string | number>]),
    ...revision.sections.flatMap((section, index) => [
      [section.heading, ["sections", index, "heading"]] as [string, Array<string | number>],
      [section.body_markdown, ["sections", index, "body_markdown"]] as [
        string,
        Array<string | number>
      ]
    ]),
    ...revision.faq.flatMap((item, index) => [
      [item.question, ["faq", index, "question"]] as [string, Array<string | number>],
      [item.answer_markdown, ["faq", index, "answer_markdown"]] as [
        string,
        Array<string | number>
      ]
    ]),
    ...revision.cta_blocks.map((item, index) => [
      item.body_markdown,
      ["cta_blocks", index, "body_markdown"]
    ] as [string, Array<string | number>])
  ];
  for (const [value, path] of generatedText) {
    if (containsInlineLink(value)) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path,
        message: "generated document text cannot contain inline links"
      });
    }
  }
});

export const ContentDraftRevisionDecisionSchema = z.enum([
  "approved",
  "needs_changes",
  "rejected",
  "deferred"
]);

export const ContentDraftRevisionReviewSchema = z
  .object({
    decision_id: z.string(),
    decision_number: z.number().int().positive(),
    work_item_id: z.string(),
    revision_id: z.string(),
    revision_digest: z.string().regex(/^[0-9a-f]{64}$/),
    reviewed_by: z.string().refine((value) => value.trim().length > 0),
    decision: ContentDraftRevisionDecisionSchema,
    notes: z.string(),
    checked_items: z
      .array(z.string().refine((value) => value.trim().length > 0))
      .default([]),
    evidence_ids: z
      .array(z.string().refine((value) => value.trim().length > 0))
      .default([]),
    created_at: z.string()
  })
  .superRefine((review, context) => {
    if (
      review.decision === "approved" &&
      (review.checked_items.length === 0 || review.evidence_ids.length === 0)
    ) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: review.checked_items.length === 0 ? ["checked_items"] : ["evidence_ids"],
        message: "approved persisted review requires checked items and evidence IDs"
      });
    }
    if (review.decision !== "approved" && review.notes.trim().length === 0) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["notes"],
        message: "non-approved persisted review requires notes"
      });
    }
  });

export const ContentDraftRevisionWorkspaceStatusSchema = z.enum([
  "empty",
  "unreviewed",
  "needs_changes",
  "approved",
  "rejected",
  "deferred"
]);

export const ContentDraftRevisionWorkspaceSchema = z
  .object({
    status: ContentDraftRevisionWorkspaceStatusSchema,
    latest_revision: ContentDraftRevisionSchema.nullable(),
    latest_review: ContentDraftRevisionReviewSchema.nullable(),
    revision_count: z.number().int().nonnegative(),
    context_current: z.boolean(),
    editor_title: z.string(),
    editor_sections: z.array(ContentDraftRevisionSectionSchema),
    can_save: z.boolean(),
    can_review: z.boolean(),
    safe_next_step: z.string()
  })
  .superRefine((workspace, context) => {
    if (workspace.status === "empty" && workspace.latest_revision !== null) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["latest_revision"],
        message: "empty revision workspace cannot expose a latest revision"
      });
    }
    if (workspace.status === "empty" && workspace.latest_review !== null) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["latest_review"],
        message: "empty revision workspace cannot expose a latest review"
      });
    }
    if (workspace.status === "empty" && workspace.revision_count !== 0) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["revision_count"],
        message: "empty revision workspace must have revision_count=0"
      });
    }
    if (workspace.status === "empty" && !workspace.context_current) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["context_current"],
        message: "empty revision workspace cannot have stale persisted context"
      });
    }
    if (
      workspace.status !== "empty" &&
      (workspace.latest_revision === null || workspace.revision_count < 1)
    ) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["latest_revision"],
        message: "non-empty revision workspace must expose a latest revision"
      });
    }
    if (workspace.status === "unreviewed" && workspace.latest_review !== null) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["latest_review"],
        message: "unreviewed revision workspace cannot expose a latest review"
      });
    }
    if (
      ["needs_changes", "approved", "rejected", "deferred"].includes(workspace.status) &&
      workspace.latest_review === null
    ) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["latest_review"],
        message: "reviewed revision workspace must expose the latest review"
      });
    }
    const latestRevision = workspace.latest_revision;
    const latestReview = workspace.latest_review;
    if (latestRevision && latestReview) {
      if (
        latestReview.revision_id !== latestRevision.revision_id ||
        latestReview.revision_digest !== latestRevision.content_digest
      ) {
        context.addIssue({
          code: z.ZodIssueCode.custom,
          path: ["latest_review"],
          message: "latest review must be bound to the exact latest revision and digest"
        });
      }
      if (workspace.status !== latestReview.decision) {
        context.addIssue({
          code: z.ZodIssueCode.custom,
          path: ["status"],
          message: "reviewed workspace status must match the latest review decision"
        });
      }
    }
    if (
      latestRevision &&
      workspace.context_current &&
      (workspace.editor_title !== latestRevision.title ||
        JSON.stringify(workspace.editor_sections) !== JSON.stringify(latestRevision.sections))
    ) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["editor_sections"],
        message: "editor state must hydrate the exact latest revision"
      });
    }
    if (
      workspace.can_review &&
      ((workspace.status !== "unreviewed" && workspace.status !== "deferred") ||
        !workspace.context_current)
    ) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["can_review"],
        message: "only unreviewed or deferred revisions can be reviewed"
      });
    }
    if (workspace.can_save && workspace.can_review) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["can_review"],
        message: "revision workspace cannot save and review at the same time"
      });
    }
    if (
      workspace.can_save &&
      (workspace.editor_title.trim().length === 0 || workspace.editor_sections.length === 0)
    ) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["can_save"],
        message: "saveable workspace requires a title and at least one editor section"
      });
    }
  });

export const ContentDraftRevisionSaveRequestSchema = z.object({
  base_revision_id: z.string().nullable(),
  title: z.string().refine((value) => value.trim().length > 0),
  sections: z.array(ContentDraftRevisionSectionSchema).min(1),
  correction_reason: z.enum(["canonical_html_alignment"]).nullable().optional(),
  created_by: z.string().refine((value) => value.trim().length > 0)
});

export const ContentDraftRevisionSaveResponseSchema = z.object({
  status: z.enum(["created", "idempotent"]),
  revision: ContentDraftRevisionSchema,
  workspace: ContentDraftRevisionWorkspaceSchema
});

export const ContentOfficialSourceLineageRebaseRequestSchema = z.object({
  expected_revision_digest: z.string().regex(/^[0-9a-f]{64}$/),
  requested_by: z.string().trim().min(1)
});

export const ContentDraftRevisionReviewRequestSchema = z
  .object({
    expected_revision_digest: z.string().regex(/^[0-9a-f]{64}$/),
    reviewed_by: z.string().refine((value) => value.trim().length > 0),
    decision: ContentDraftRevisionDecisionSchema,
    notes: z.string(),
    checked_items: z
      .array(z.string().refine((value) => value.trim().length > 0))
      .default([]),
    evidence_ids: z
      .array(z.string().refine((value) => value.trim().length > 0))
      .default([])
  })
  .superRefine((review, context) => {
    if (
      review.decision === "approved" &&
      (review.checked_items.length === 0 || review.evidence_ids.length === 0)
    ) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: review.checked_items.length === 0 ? ["checked_items"] : ["evidence_ids"],
        message: "approved review requires checked items and evidence IDs"
      });
    }
    if (review.decision !== "approved" && review.notes.trim().length === 0) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["notes"],
        message: "non-approved review requires notes"
      });
    }
  });

export const ContentDraftRevisionReviewResponseSchema = z.object({
  status: z.enum(["recorded", "idempotent"]),
  review: ContentDraftRevisionReviewSchema,
  workspace: ContentDraftRevisionWorkspaceSchema
});

export const ContentRevisionHtmlPackageManifestSchema = z.object({
  work_item_id: z.string().min(1),
  revision_id: z.string().min(1),
  content_digest: z.string().regex(/^[0-9a-f]{64}$/),
  final_canonical_url: z.string().min(1),
  evidence_ids: z.array(z.string()).default([]),
  source_material_ids: z.array(z.string()).default([]),
  knowledge_card_ids: z.array(z.string()).default([]),
  official_source_references: z.array(ContentDraftRevisionOfficialSourceReferenceSchema).default([]),
  section_count: z.number().int().positive()
});

export const ContentRevisionHtmlPackageResponseSchema = z.object({
  manifest: ContentRevisionHtmlPackageManifestSchema,
  file_name: z.string().regex(/^wilq-exact-revision-[A-Za-z0-9_-]+\.html$/),
  html_document: z.string().min(1)
});

export const ContentEditorialIntegrityRevisionSchema = z.object({
  revision_id: z.string().min(1),
  content_digest: z.string().regex(/^[0-9a-f]{64}$/),
  revision_number: z.number().int().positive()
});

export const ContentEditorialIntegrityHumanReviewSchema = z.object({
  decision: ContentDraftRevisionDecisionSchema,
  reviewed_by: z.string().min(1)
});

export const ContentEditorialIntegrityScopeSchema = z.object({
  section_ids: z.array(z.string()).default([]),
  fields: z.array(z.enum(["body", "title", "faq", "cta", "links"])).default([])
});

export const ContentEditorialStructuralInvariantsSchema = z.object({
  section_ids_unchanged: z.boolean(),
  section_order_unchanged: z.boolean(),
  headings_unchanged: z.boolean(),
  title_unchanged: z.boolean(),
  faq_unchanged: z.boolean(),
  cta_semantics_unchanged: z.boolean(),
  links_unchanged: z.boolean(),
  evidence_lineage_unchanged: z.boolean()
});

export const ContentProtectedContentUnitSchema = z.object({
  unit_id: z.string().min(1),
  section_id: z.string().min(1),
  section_heading: z.string().min(1),
  claim_ids: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()).default([]),
  before_excerpt: z.string().min(1),
  after_excerpt: z.string().nullable(),
  status: z.enum(["preserved", "changed", "removed"])
});

export const ContentRepresentationAlignmentSchema = z.object({
  section_id: z.string().min(1),
  section_heading: z.string().min(1),
  source_body_sha256: z.string().regex(/^[0-9a-f]{64}$/),
  rendered_html_sha256: z.string().regex(/^[0-9a-f]{64}$/).nullable(),
  normalized_source_text_sha256: z.string().regex(/^[0-9a-f]{64}$/),
  normalized_rendered_text_sha256: z.string().regex(/^[0-9a-f]{64}$/).nullable(),
  status: z.enum(["aligned", "mismatch"])
});

export const ContentEditorialLintSignalSchema = z.object({
  code: z.string().min(1),
  section_id: z.string().nullable(),
  occurrences: z.number().int().positive(),
  excerpts: z.array(z.string()).default([]),
  reason: z.string().min(1)
});

export const ContentEditorialIntegrityReportSchema = z.object({
  work_item_id: z.string().min(1),
  baseline_revision: ContentEditorialIntegrityRevisionSchema,
  direct_parent_revision: ContentEditorialIntegrityRevisionSchema.nullable(),
  child_revision: ContentEditorialIntegrityRevisionSchema,
  human_review: ContentEditorialIntegrityHumanReviewSchema.nullable(),
  observed_scope: ContentEditorialIntegrityScopeSchema,
  structural_invariants: ContentEditorialStructuralInvariantsSchema,
  protected_content_units: z.array(ContentProtectedContentUnitSchema).default([]),
  representation_alignment: z.array(ContentRepresentationAlignmentSchema).default([]),
  lint_signals: z.array(ContentEditorialLintSignalSchema).default([]),
  human_readable_diff: z.string().min(1),
  result: z.enum(["integrity_ok", "invalid_representation", "structural_change_observed"])
});

export const ContentDraftRevisionConflictSchema = z.object({
  status: z.literal("conflict"),
  code: z.enum([
    "workspace_not_saveable",
    "revision_not_reviewable",
    "apply_in_progress",
    "stale_base",
    "revision_not_found",
    "stale_revision",
    "stale_review",
    "digest_mismatch",
    "official_source_lineage_unavailable"
  ]),
  current_revision_id: z.string().nullable(),
  current_digest: z.string().regex(/^[0-9a-f]{64}$/).nullable(),
  safe_next_step: z.string()
});

export const ContentCodexRuntimeTraceSchema = z.object({
  status: z.enum(["not_started", "completed", "blocked", "failed"]),
  run_id: z.string().nullable().optional(),
  thread_id: z.string().nullable(),
  turn_id: z.string().nullable(),
  event_methods: z.array(z.string()).default([]),
  item_types: z.array(z.string()).default([]),
  external_call_attempted: z.boolean()
});

export const ContentRevisionRepairProposalRequestSchema = z.object({
  expected_base_digest: z.string().regex(/^[0-9a-f]{64}$/),
  selected_section_ids: z.array(z.string().trim().min(1)).default([]),
  selected_cta_ids: z.array(z.string().trim().min(1)).default([]),
  requested_by: z.string().trim().min(1)
}).superRefine((request, context) => {
  const selectedCount = request.selected_section_ids.length + request.selected_cta_ids.length;
  if (selectedCount !== 1) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      message: "repair proposal requires exactly one persisted section or CTA"
    });
  }
  if (
    new Set(request.selected_section_ids).size !== request.selected_section_ids.length ||
    new Set(request.selected_cta_ids).size !== request.selected_cta_ids.length
  ) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      message: "repair proposal component IDs must be unique"
    });
  }
});

export const ContentRevisionRepairProposalBlockerSchema = z.object({
  code: z.enum([
    "missing_planning_binding",
    "missing_base_revision",
    "stale_base_revision",
    "revision_not_ready_for_proposal",
    "stale_content_context",
    "missing_generation_contract",
    "unknown_selected_section",
    "unknown_selected_cta",
    "ambiguous_claim_marker",
    "runtime_blocked",
    "runtime_failed",
    "invalid_structured_output",
    "section_scope_mismatch",
    "proposal_contract_blocked",
    "quality_blocked",
    "revision_conflict"
  ]),
  label: z.string().min(1),
  reason: z.string().min(1),
  next_step: z.string().min(1),
  source_codes: z.array(z.string()).default([])
});

export const ContentRevisionRepairProposalResponseSchema = z.object({
  status: z.enum(["created", "idempotent", "blocked", "failed", "conflict"]),
  run_id: z.string().nullable().optional(),
  work_item_id: z.string().min(1),
  base_revision_id: z.string().min(1),
  selected_section_headings: z.array(z.string()).default([]),
  selected_cta_ids: z.array(z.string()).default([]),
  revision: ContentDraftRevisionSchema.nullable().optional(),
  quality_review: ContentQualityReviewSchema.nullable().optional(),
  quality_review_scope: z.enum([
    "persisted_selected_sections_and_declared_lineage",
    "persisted_selected_components_and_declared_lineage"
  ]),
  semantic_review_required: z.literal(true),
  runtime: ContentCodexRuntimeTraceSchema,
  evidence_ids: z.array(z.string()).default([]),
  source_connectors: z.array(z.string()).default([]),
  blockers: z.array(ContentRevisionRepairProposalBlockerSchema).default([]),
  safe_next_step: z.string().min(1),
  publish_ready: z.literal(false)
}).superRefine((response, context) => {
  if (["created", "idempotent"].includes(response.status)) {
    if (!response.run_id || !response.revision || !response.quality_review || response.quality_review.verdict === "blocked" || response.blockers.length) {
      context.addIssue({ code: z.ZodIssueCode.custom, message: "created repair proposal requires a reviewable child revision" });
    }
  } else if (response.revision || !response.blockers.length) {
    context.addIssue({ code: z.ZodIssueCode.custom, message: "non-created repair proposal requires blockers without a revision" });
  }
});

 export const ContentWorkflowOperatorStepIdSchema = z.enum(
  CONTENT_WORKFLOW_OPERATOR_STEP_ORDER
);

export const ContentWorkflowOperatorStepPhaseSchema = z.enum([
  "complete",
  "current",
  "pending"
]);

export const ContentWorkflowOperatorStepReadinessSchema = z.enum([
  "ready",
  "review_required",
  "blocked"
]);

export const ContentWorkflowOperatorStepBlockerSchema = z.object({
  code: z.string(),
  label: z.string(),
  reason: z.string()
});

export const ContentWorkflowOperatorStepSchema = z.object({
  id: ContentWorkflowOperatorStepIdSchema,
  title: z.string(),
  phase: ContentWorkflowOperatorStepPhaseSchema,
  readiness: ContentWorkflowOperatorStepReadinessSchema,
  status_label: z.string(),
  summary: z.string(),
  can_open: z.boolean(),
  can_submit: z.boolean(),
  blocker: ContentWorkflowOperatorStepBlockerSchema.nullable(),
  safe_next_step: z.string()
});

export const ContentWorkflowOperatorJourneySchema = z.object({
  current_step_id: ContentWorkflowOperatorStepIdSchema,
  steps: z.array(ContentWorkflowOperatorStepSchema).length(5)
}).superRefine((journey, context) => {
  const stepIds = journey.steps.map((step) => step.id);
  if (new Set(stepIds).size !== stepIds.length) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["steps"],
      message: "steps must contain five unique operator step IDs"
    });
  }
  if (
    stepIds.some(
      (stepId, index) => stepId !== CONTENT_WORKFLOW_OPERATOR_STEP_ORDER[index]
    )
  ) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["steps"],
      message: "steps must use the canonical five-step order"
    });
  }
  const currentSteps = journey.steps.filter((step) => step.phase === "current");
  if (
    currentSteps.length !== 1 ||
    currentSteps[0]?.id !== journey.current_step_id
  ) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["current_step_id"],
      message: "current_step_id must identify the single current operator step"
    });
  }
});

export const ContentWorkItemServiceProfileBindingStatusSchema = z.enum([
  "not_evaluated",
  "bound",
  "unbound"
]);

export const ContentWorkItemServiceProfileDecisionStatusSchema = z.enum([
  "not_evaluated",
  "ready",
  "review_required",
  "blocked"
]);

export const ContentWorkItemServiceCandidateSchema = z.object({
  service_card_id: z.string().min(1),
  service_label: z.string().min(1),
  lifecycle_status: ContentKnowledgeLifecycleStatusSchema,
  lifecycle_label: z.string().min(1),
  matched_terms: z.array(z.string().min(1)).nonempty(),
  match_reasons: z.array(z.string().min(1)).nonempty(),
  recommended: z.boolean()
});

export const ContentWorkItemServiceProfileContextSchema = z.object({
  binding_status: ContentWorkItemServiceProfileBindingStatusSchema,
  decision_status: ContentWorkItemServiceProfileDecisionStatusSchema,
  status_label: z.string(),
  reason: z.string(),
  service_card_id: z.string().nullable().optional(),
  service_label: z.string().nullable().optional(),
  service_status: z.string().nullable().optional(),
  service_status_label: z.string().default(""),
  service_selection_confirmed: z.boolean().default(false),
  human_override_review_required: z.boolean().default(false),
  service_candidates: z.array(ContentWorkItemServiceCandidateSchema).default([]),
  freshness_label: z.string().default(""),
  freshness_as_of: z.string().nullable().optional(),
  source_summary_label: z.string().default(""),
  allowed_claims: z.array(z.string()).default([]),
  claims_needing_review: z.array(z.string()).default([]),
  blocked_claims: z.array(z.string()).default([]),
  claim_policy_scope_label: z.string().default(""),
  evidence_requirements: z.array(z.string()).default([]),
  missing_contracts: z.array(z.string()).default([]),
  safe_next_step: z.string(),
  source_connectors: z.array(z.string()).default([]),
  source_fact_ids: z.array(z.string()).default([]),
  source_material_ids: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()).default([]),
  knowledge_card_ids: z.array(z.string()).default([]),
  review_action_id: z.string().nullable().optional(),
  review_action_label: z.string().nullable().optional(),
  minimum_cta_blocks: z.number().int().min(1).max(4).optional(),
  cta_patterns: z.array(z.string().trim().min(1)).max(4).optional()
});

const ContentWorkItemServiceProfileContextDefault = {
  binding_status: "not_evaluated" as const,
  decision_status: "not_evaluated" as const,
  status_label: "Profil usługi nie został jeszcze oceniony",
  reason:
    "Workflow nie ma jeszcze bezpiecznego snapshotu do sprawdzenia usługi, więc WILQ jej nie przypisuje.",
  service_status_label: "",
  service_selection_confirmed: false,
  human_override_review_required: false,
  service_candidates: [],
  freshness_label: "",
  freshness_as_of: null,
  source_summary_label: "",
  allowed_claims: [],
  claims_needing_review: [],
  blocked_claims: [],
  claim_policy_scope_label:
    "Nie ma jeszcze przypisanej karty usługi, więc WILQ nie pokazuje polityki twierdzeń dla tego work itemu.",
  evidence_requirements: [],
  missing_contracts: [],
  safe_next_step: "Najpierw usuń blocker workflow, potem sprawdź profil usługi.",
  source_connectors: [],
  source_fact_ids: [],
  source_material_ids: [],
  evidence_ids: [],
  knowledge_card_ids: [],
  minimum_cta_blocks: 1,
  cta_patterns: []
};

export const ContentPlanningDecisionSchema = z.object({
  decision_id: z.string().min(1),
  decision_number: z.number().int().positive(),
  work_item_id: z.string().min(1),
  stage: z.enum(["scope", "section_map"]),
  planning_digest: z.string().regex(/^[0-9a-f]{64}$/),
  service_card_id: z.string().nullable().optional(),
  human_override_review_required: z.boolean().default(false),
  decision: z.enum(["approved", "needs_changes"]),
  reviewed_by: z.string().min(1),
  checked_items: z.array(z.string()),
  notes: z.string(),
  created_at: z.string()
});

const ContentSearchDemandRowSchema = z.object({
  source_kind: z.enum(["gsc_query", "ads_search_term", "keyword_planner"]),
  source_connector: z.enum(["google_search_console", "google_ads"]),
  term: z.string().min(1),
  page: z.string().min(1),
  landing_match_tiers: z.array(
    z.enum(["exact", "tracking_only", "host_alias"])
  ).default([]),
  service_card_id: z.string().nullable(),
  service_binding_status: z.enum([
    "not_required",
    "unbound",
    "ambiguous",
    "review_required",
    "approved_current"
  ]).optional(),
  service_candidate_ids: z.array(z.string()).optional(),
  service_lifecycle_statuses: z.array(z.string()).optional(),
  alignment_basis: z.enum([
    "legacy_unspecified",
    "gsc_exact_page",
    "direct_page_service_scope",
    "same_window_search_term_landing"
  ]).default("legacy_unspecified"),
  review_required: z.boolean().default(true),
  section_headings: z.array(z.string()),
  section_mapping_status: z.enum(["intent_relevance", "lexical_relevance", "page_only"]),
  period: z.string().min(1),
  freshness: z.enum(["fresh", "stale", "missing", "blocked"]),
  collected_at: z.string().nullable(),
  evidence_ids: z.array(z.string()).min(1),
  impressions: z.number().int().nullable(),
  clicks: z.number().int().nullable(),
  ctr: z.number().nullable(),
  average_position: z.number().nullable(),
  average_monthly_searches: z.number().int().nullable(),
  cost_micros: z.number().int().nullable().default(null),
  conversions: z.number().nullable().default(null),
  conversion_value: z.number().nullable().default(null)
});

const ContentSearchDemandEvidenceSchema = z.object({
  status: z.enum(["available", "missing"]),
  gsc_query_rows: z.array(ContentSearchDemandRowSchema),
  ads_term_rows: z.array(ContentSearchDemandRowSchema),
  keyword_planner_rows: z.array(ContentSearchDemandRowSchema),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  optional_ads_status: z.enum([
    "exact_rows_available",
    "not_exactly_mapped",
    "stale",
    "blocked"
  ]),
  optional_ads_evidence_ids: z.array(z.string()).default([]),
  optional_ads_blockers: z.array(z.string()).default([]),
  safe_next_step: z.string().min(1)
}).superRefine((demand, context) => {
  const exactRows = [...demand.ads_term_rows, ...demand.keyword_planner_rows];
  if (demand.optional_ads_status === "blocked" && (
    demand.optional_ads_evidence_ids.length === 0 || demand.optional_ads_blockers.length === 0
  )) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["optional_ads_status"],
      message: "blocked Ads demand requires evidence and blockers"
    });
  }
  if (demand.optional_ads_status === "blocked" && exactRows.length > 0) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["optional_ads_status"],
      message: "blocked Ads demand cannot expose usable rows"
    });
  }
  if (demand.optional_ads_status !== "blocked" && demand.optional_ads_blockers.length > 0) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["optional_ads_blockers"],
      message: "non-blocked Ads demand cannot expose blockers"
    });
  }
  if (demand.optional_ads_status === "exact_rows_available" && (
    exactRows.length === 0 || demand.optional_ads_evidence_ids.length === 0
  )) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["optional_ads_status"],
      message: "exact Ads demand requires rows and evidence"
    });
  }
  if (demand.optional_ads_status === "stale" && (
    demand.optional_ads_evidence_ids.length === 0 ||
    exactRows.some((row) => row.freshness !== "stale")
  )) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["optional_ads_status"],
      message: "stale Ads demand requires evidence and only stale rows"
    });
  }
  if (demand.optional_ads_status === "not_exactly_mapped" && exactRows.length > 0) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["optional_ads_status"],
      message: "unmapped Ads demand cannot expose exact rows"
    });
  }
});

export const ContentPlanningInventoryDispositionSchema = z.enum([
  "preserve",
  "merge",
  "rewrite",
  "remove_review_required",
  "create"
]);

export const ContentPlanningPageAssetsSchema = z.object({
  title: z.string().default(""),
  h1: z.string().default(""),
  lead: z.string().default(""),
  meta_title: z.string().default(""),
  meta_description: z.string().default("")
});

export const ContentPlanningFaqItemSchema = z.object({
  question: z.string().min(1),
  purpose: z.string().min(1),
  query_terms: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()).default([]),
  claim_ids: z.array(z.string()).default([])
});

export const ContentPlanningCtaBlockSchema = z.object({
  placement: z.string().min(1),
  purpose: z.string().min(1),
  copy_direction: z.string().min(1),
  evidence_ids: z.array(z.string()).default([]),
  claim_ids: z.array(z.string()).default([])
});

export const ContentPlanningInternalLinkSchema = z.object({
  placement: z.string().min(1),
  target_url: z.string().min(1),
  anchor_direction: z.string().min(1),
  evidence_ids: z.array(z.string()).default([]),
  claim_ids: z.array(z.string()).default([])
});

export const ContentPlanningConditionalHypothesisSchema = z.object({
  channel: z.enum(["google_ads", "social"]),
  hypothesis: z.string().min(1),
  evidence_ids: z.array(z.string()).min(1),
  review_required: z.literal(true).default(true)
});

export const ContentPlanningMeasurementPlanSchema = z.object({
  metrics_to_watch: z.array(z.string()).default([]),
  baseline_evidence_ids: z.array(z.string()).default([]),
  observation_rule: z.string().default(""),
  success_claim_rule: z.string().default("")
});

export const ContentPlanningMetricComparisonSchema = z.object({
  source_connector: z.enum(["google_search_console", "google_analytics_4"]),
  status: z.enum(["available", "not_available", "ambiguous"]),
  baseline_period: z.string().nullable().optional(),
  comparison_period: z.string().nullable().optional(),
  metric_names: z.array(z.string()).default([]),
  baseline_values: z.record(z.string(), z.number()).default({}),
  comparison_values: z.record(z.string(), z.number()).default({}),
  evidence_ids: z.array(z.string()).default([]),
  reason: z.string()
});

export const ContentPlanningProposalSchema = z.object({
  work_item_id: z.string().min(1),
  planning_digest: z.string().regex(/^[0-9a-f]{64}$/),
  proposal_id: z.string().nullable().optional(),
  proposal_version: z.number().int().positive().nullable().optional(),
  codex_run_id: z.string().nullable().optional(),
  generation_status: z.enum(["baseline", "codex_generated"]).default("baseline"),
  input_schema_version: z.string().default("wilq_content_planning_input_v1"),
  criteria_version: z.string().default("wilq_people_first_planning_v5"),
  planning_input_digest: z.string().regex(/^[0-9a-f]{64}$/).nullable().optional(),
  goal: z.enum(["refresh_existing", "new_page"]).default("refresh_existing"),
  final_canonical_url: z.string().min(1).nullable().optional(),
  proposed_ia_location: z.string().trim().min(3).nullable().optional(),
  new_page_document_identity: ContentNewPageDocumentIdentitySchema.nullable().optional(),
  service_card_id: z.string().nullable(),
  service_label: z.string().nullable(),
  service_selection_confirmed: z.boolean().default(false),
  human_override_review_required: z.boolean().default(false),
  target_reader: z.string().min(1),
  buyer_problem: z.string().min(1),
  buyer_trigger: z.string().min(1),
  search_intent: z.string().min(1),
  angle: z.string().default(""),
  value_proposition: z.string().default(""),
  cta_direction: z.string().min(1),
  minimum_cta_blocks: z.number().int().min(1).max(4).optional(),
  required_cta_patterns: z.array(z.string().trim().min(1)).max(4).optional(),
  internal_link_directions: z.array(z.string()),
  sections: z.array(z.object({
    section_id: z.string().default(""),
    heading: z.string().min(1),
    purpose: z.string().min(1),
    reader_question: z.string().default(""),
    inventory_disposition: ContentPlanningInventoryDispositionSchema.default("create"),
    inventory_section_id: z.string().nullable().optional(),
    inventory_heading: z.string().nullable().optional(),
    query_terms: z.array(z.string()).default([]),
    evidence_ids: z.array(z.string()),
    claim_ids: z.array(z.string()).default([]),
    source_material_ids: z.array(z.string()).default([]),
    knowledge_card_ids: z.array(z.string()).default([]),
    regulatory_requirement_ids: z.array(z.string()).default([])
  })).min(1),
  inventory_mapping: z.array(z.object({
    inventory_section_id: z.string().min(1),
    inventory_heading: z.string().min(1),
    status: z.enum(["mapped", "unmapped", "ambiguous", "excluded"]),
    mapped_section_id: z.string().nullable().optional(),
    mapped_section_heading: z.string().nullable().optional(),
    disposition: ContentPlanningInventoryDispositionSchema.nullable().optional(),
    reason: z.string().default(""),
    evidence_ids: z.array(z.string()).default([])
  })).optional(),
  search_demand: ContentSearchDemandEvidenceSchema,
  page_assets: ContentPlanningPageAssetsSchema.default({
    title: "",
    h1: "",
    lead: "",
    meta_title: "",
    meta_description: ""
  }),
  faq: z.array(ContentPlanningFaqItemSchema).default([]),
  cta_blocks: z.array(ContentPlanningCtaBlockSchema).default([]),
  internal_links: z.array(ContentPlanningInternalLinkSchema).default([]),
  conditional_hypotheses: z.array(ContentPlanningConditionalHypothesisSchema).default([]),
  measurement_plan: ContentPlanningMeasurementPlanSchema.default({
    metrics_to_watch: [],
    baseline_evidence_ids: [],
    observation_rule: "",
    success_claim_rule: ""
  }),
  measurement_metrics: z.array(z.string()).optional(),
  measurement_baseline_evidence_ids: z.array(z.string()).optional(),
  evidence_ids: z.array(z.string()),
  source_connectors: z.array(z.string()),
  source_material_ids: z.array(z.string()).default([]),
  knowledge_card_ids: z.array(z.string()).default([]),
  created_at: z.string().nullable().optional()
}).superRefine((proposal, context) => {
  if (proposal.goal === "refresh_existing") {
    if (!proposal.final_canonical_url?.trim()) {
      context.addIssue({ code: z.ZodIssueCode.custom, path: ["final_canonical_url"], message: "Refresh proposal requires final_canonical_url." });
    }
    if (proposal.proposed_ia_location || proposal.new_page_document_identity) {
      context.addIssue({ code: z.ZodIssueCode.custom, message: "Refresh proposal cannot carry new-page identity." });
    }
    return;
  }
  if (proposal.final_canonical_url !== null || !proposal.proposed_ia_location?.trim() || !proposal.new_page_document_identity) {
    context.addIssue({ code: z.ZodIssueCode.custom, message: "New-page proposal requires exact IA and document identity without a public URL." });
    return;
  }
  if (
    proposal.new_page_document_identity.work_item_id !== proposal.work_item_id ||
    proposal.new_page_document_identity.proposed_ia_location !== proposal.proposed_ia_location ||
    (proposal.inventory_mapping?.length ?? 0) > 0
  ) {
    context.addIssue({ code: z.ZodIssueCode.custom, message: "New-page proposal identity or inventory is contradictory." });
  }
  proposal.sections.forEach((section, index) => {
    if (
      section.inventory_disposition !== "create" ||
      section.inventory_section_id !== null ||
      section.inventory_heading !== null
    ) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["sections", index],
        message: "New-page proposal sections cannot reference existing-page inventory."
      });
    }
  });
});

export const ContentPlanningWorkspaceSchema = z
  .object({
    proposal: ContentPlanningProposalSchema,
    scope_decision: ContentPlanningDecisionSchema.nullable(),
    section_map_decision: ContentPlanningDecisionSchema.nullable(),
    scope_current: z.boolean(),
    section_map_current: z.boolean()
  })
  .superRefine((workspace, context) => {
    for (const [field, decision] of [
      ["scope_decision", workspace.scope_decision],
      ["section_map_decision", workspace.section_map_decision]
    ] as const) {
      if (!decision) continue;
      if (
        decision.work_item_id !== workspace.proposal.work_item_id ||
        decision.planning_digest !== workspace.proposal.planning_digest ||
        (decision.service_card_id !== null && decision.service_card_id !== workspace.proposal.service_card_id)
      ) {
        context.addIssue({
          code: z.ZodIssueCode.custom,
          path: [field],
          message: "Planning decision must bind to the exact proposal."
        });
      }
    }
    const scopeCurrent = Boolean(
      workspace.scope_decision?.decision === "approved" &&
      workspace.scope_decision.work_item_id === workspace.proposal.work_item_id &&
      workspace.scope_decision.planning_digest === workspace.proposal.planning_digest &&
      (workspace.scope_decision.service_card_id === null ||
        workspace.scope_decision.service_card_id === workspace.proposal.service_card_id)
    );
    if (workspace.scope_current !== scopeCurrent) {
      context.addIssue({ code: z.ZodIssueCode.custom, path: ["scope_current"], message: "scope_current must reflect the exact scope decision." });
    }
    const sectionMapCurrent = Boolean(
      workspace.proposal.generation_status === "codex_generated" &&
      workspace.proposal.proposal_id &&
      workspace.proposal.sections.length
    );
    if (workspace.section_map_current !== sectionMapCurrent) {
      context.addIssue({ code: z.ZodIssueCode.custom, path: ["section_map_current"], message: "section_map_current must reflect the exact generated proposal." });
    }
  });

export const ContentPlanningProposalRequestSchema = z.object({
  service_card_id: z.string().min(1),
  expected_planning_input_digest: z.string().regex(/^[0-9a-f]{64}$/),
  operator_hint: z.string().max(500).default(""),
  requested_by: z.string().min(1),
  regenerate_stale_mapping: z.boolean().default(false),
  regenerate_after_review: z.boolean().default(false)
});

export const ContentPlanningProposalBlockerSchema = z.object({
  code: z.string().min(1),
  label: z.string().min(1),
  reason: z.string().min(1),
  next_step: z.string().min(1),
  source_codes: z.array(z.string()).default([])
});

export const ContentPlanningSourceAssessmentSchema = z.object({
  source: z.enum([
    "wordpress",
    "service_profile",
    "gsc",
    "ga4",
    "google_ads",
    "ahrefs",
    "keyword_planner",
    "merchant",
    "localo",
    "social"
  ]),
  status: z.enum(["used", "not_applicable", "missing", "stale", "blocked"]),
  reason: z.string().min(1),
  landing_match_tiers: z.array(
    z.enum(["exact", "tracking_only", "host_alias"])
  ).default([]),
  evidence_ids: z.array(z.string()).default([]),
  knowledge_card_ids: z.array(z.string()).default([])
});

export const ContentPlanningSourceFactPreviewSchema = z.object({
  fact_id: z.string().min(1),
  summary: z.string().min(1),
  source_connector: z.string().min(1),
  evidence_ids: z.array(z.string()).min(1),
  knowledge_card_ids: z.array(z.string()).default([]),
  source_fact_ids: z.array(z.string()).default([]),
  source_material_ids: z.array(z.string()).default([]),
  regulatory_requirement_ids: z.array(z.string()).default([])
});

export const ContentRegulatorySourceReviewCommandSchema = z.object({
  candidate_id: z.string().trim().min(1),
  expected_source_url: z.string().url(),
  expected_profile_version: z.string().trim().min(1),
  expected_source_snapshot_id: z.string().trim().min(1),
  expected_source_snapshot_digest: z.string().regex(/^[0-9a-f]{64}$/),
  reviewed_fact: z.string().trim().min(20).max(2000),
  covered_requirement_ids: z.array(z.string().trim().min(1)).min(1),
  decision: z.enum(["accepted", "rejected"]),
  reviewer: z.string().trim().min(1).max(200)
});

export const ContentRegulatorySourceReviewSchema = ContentRegulatorySourceReviewCommandSchema.extend({
  review_id: z.string().min(1),
  profile_id: z.string().trim().min(1),
  service_card_ids: z.array(z.string().trim().min(1)).min(1),
  source_url: z.string().url(),
  source_title: z.string().trim().min(1),
  observed_on: z.string().min(1),
  source_snapshot_id: z.string().trim().min(1),
  source_snapshot_digest: z.string().regex(/^[0-9a-f]{64}$/),
  reviewed_at: z.string().datetime()
}).omit({
  expected_source_url: true,
  expected_profile_version: true,
  expected_source_snapshot_id: true,
  expected_source_snapshot_digest: true
});

export const ContentRegulatorySourceReviewListSchema = z.object({
  reviews: z.array(ContentRegulatorySourceReviewSchema).default([])
});

export const ContentRegulatorySourceReviewConflictSchema = z.object({
  code: z.enum(["candidate_changed", "source_snapshot_missing", "source_snapshot_changed", "source_proposal_stale"]),
  label: z.string().trim().min(1),
  reason: z.string().trim().min(1),
  safe_next_step: z.string().trim().min(1)
});

export const ContentRegulatorySourceSnapshotSchema = z.object({
  snapshot_id: z.string().trim().min(1),
  candidate_id: z.string().trim().min(1),
  profile_id: z.string().trim().min(1),
  profile_version: z.string().trim().min(1),
  source_url: z.string().url(),
  content_digest: z.string().regex(/^[0-9a-f]{64}$/),
  content_type: z.string().trim().min(1),
  byte_length: z.number().int().positive().max(12 * 1024 * 1024),
  observed_at: z.string().datetime()
});

export const ContentRegulatorySourceSnapshotReadResponseSchema = z.object({
  status: z.enum(["captured", "blocked"]),
  snapshot: ContentRegulatorySourceSnapshotSchema.nullable().optional(),
  reason: z.string().trim().min(1),
  safe_next_step: z.string().trim().min(1)
}).superRefine((response, context) => {
  if (response.status === "captured" && !response.snapshot) {
    context.addIssue({ code: z.ZodIssueCode.custom, message: "Captured source read requires a snapshot." });
  }
  if (response.status === "blocked" && response.snapshot) {
    context.addIssue({ code: z.ZodIssueCode.custom, message: "Blocked source read cannot expose a snapshot." });
  }
});

export const ContentRegulatorySourceFactProposalSchema = z.object({
  proposal_id: z.string().trim().min(1),
  candidate_id: z.string().trim().min(1),
  profile_id: z.string().trim().min(1),
  profile_version: z.string().trim().min(1),
  source_url: z.string().url(),
  source_title: z.string().trim().min(1),
  source_snapshot_id: z.string().trim().min(1),
  source_snapshot_digest: z.string().regex(/^[0-9a-f]{64}$/),
  observed_on: z.string().min(1),
  proposed_fact: z.string().trim().min(20).max(2000),
  covered_requirement_ids: z.array(z.string().trim().min(1)).min(1),
  codex_run_id: z.string().trim().min(1),
  status: z.literal("ready"),
  human_review_required: z.literal(true),
  created_at: z.string().datetime()
});

export const ContentRegulatorySourceFactProposalResponseSchema = z.object({
  status: z.enum(["ready", "not_generated", "blocked", "failed"]),
  proposal: ContentRegulatorySourceFactProposalSchema.nullable().optional(),
  reason: z.string().trim().min(1),
  safe_next_step: z.string().trim().min(1)
}).superRefine((response, context) => {
  if ((response.status === "ready") !== Boolean(response.proposal)) {
    context.addIssue({ code: z.ZodIssueCode.custom, message: "Only ready source proposal response may contain proposal." });
  }
});

export const ContentRegulatorySourceFactProposalReviewCommandSchema = z.object({
  expected_source_snapshot_id: z.string().trim().min(1),
  expected_source_snapshot_digest: z.string().regex(/^[0-9a-f]{64}$/),
  decision: z.enum(["accepted", "rejected"]),
  reviewer: z.string().trim().min(1).max(200)
});

const contentPlanningSourceNames = [
  "wordpress",
  "service_profile",
  "gsc",
  "ga4",
  "google_ads",
  "ahrefs",
  "keyword_planner",
  "merchant",
  "localo",
  "social"
] as const;

export const ContentPlanningInputSummarySchema = z.object({
  // Optional only for parsing historical proposal records. Every current API
  // producer supplies this discriminator.
  goal: z.enum(["refresh_existing", "new_page"]).optional(),
  final_canonical_url: z.string().min(1).nullable().optional(),
  proposed_ia_location: z.string().min(3).nullable().optional(),
  service_label: z.string().min(1),
  inventory_status: z.enum(["available", "missing", "not_applicable"]),
  content_inventory_status: z.enum(["available", "missing", "not_applicable"]).optional(),
  acf_section_inventory_status: z.enum(["available", "missing", "not_applicable"]).optional(),
  source_assessments: z.array(ContentPlanningSourceAssessmentSchema).min(10),
  source_fact_count: z.number().int().nonnegative(),
  source_fact_ids: z.array(z.string()).default([]),
  source_material_ids: z.array(z.string()).default([]),
  source_fact_previews: z.array(ContentPlanningSourceFactPreviewSchema).optional(),
  gsc_query_rows: z.array(ContentSearchDemandRowSchema).default([]),
  regulatory_profile_id: z.string().min(1).nullable().optional(),
  regulatory_profile_version: z.string().min(1).nullable().optional(),
  // Present on current regulated planning inputs. Optional only so historical
  // persisted proposal summaries remain readable.
  regulatory_requirements: z.array(z.object({
    id: z.string().trim().min(1),
    label: z.string().trim().min(1),
    reason: z.string().trim().min(1),
    document_assertions: z.array(z.object({
      id: z.string().trim().min(1),
      label: z.string().trim().min(1),
      required_any_of: z.array(z.string().trim().min(1)).min(1)
    })).default([])
  })).optional(),
  regulatory_requirement_ids: z.array(z.string().min(1)).default([]),
  regulatory_source_fact_ids: z.array(z.string().min(1)).default([]),
  regulatory_requirement_coverage: z.array(z.object({
    requirement_id: z.string().min(1),
    source_fact_ids: z.array(z.string().min(1)).default([]),
    evidence_ids: z.array(z.string().min(1)).default([])
  })).default([]),
  regulatory_review_candidates: z.array(ContentRegulatoryReviewCandidateSchema).default([]),
  evidence_id_count: z.number().int().nonnegative(),
  knowledge_card_count: z.number().int().nonnegative(),
  measurement_metrics: z.array(z.string()).default([]),
  // Optional for read compatibility with planning responses created before
  // exact page-scoped comparisons were exposed; new API responses populate it.
  metric_comparisons: z.array(ContentPlanningMetricComparisonSchema).optional()
}).superRefine((summary, context) => {
  const sources = summary.source_assessments.map((assessment) => assessment.source);
  if (
    sources.length !== contentPlanningSourceNames.length ||
    new Set(sources).size !== contentPlanningSourceNames.length ||
    contentPlanningSourceNames.some((source) => !sources.includes(source))
  ) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["source_assessments"],
      message: "Every planning source must appear exactly once."
    });
  }
  const goal = summary.goal ?? "refresh_existing";
  const inventoryStatuses = [
    summary.inventory_status,
    summary.content_inventory_status,
    summary.acf_section_inventory_status
  ];
  if (goal === "new_page") {
    if (summary.final_canonical_url !== null) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["final_canonical_url"],
        message: "New-page planning cannot claim a public canonical URL."
      });
    }
    if (!summary.proposed_ia_location?.trim()) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["proposed_ia_location"],
        message: "New-page planning requires an IA location."
      });
    }
    if (inventoryStatuses.some((status) => status !== "not_applicable")) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["inventory_status"],
        message: "New-page planning cannot carry existing-page inventory."
      });
    }
    if ((summary.metric_comparisons ?? []).length > 0) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["metric_comparisons"],
        message: "New-page planning cannot carry page metric comparisons."
      });
    }
    if (summary.gsc_query_rows.length > 0) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["gsc_query_rows"],
        message: "New-page planning cannot carry historic GSC query rows."
      });
    }
  } else {
    if (!summary.final_canonical_url?.trim()) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["final_canonical_url"],
        message: "Refresh planning requires final_canonical_url."
      });
    }
    if (summary.inventory_status === "not_applicable") {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["inventory_status"],
        message: "Refresh planning requires existing-page inventory."
      });
    }
  }
  const profileBound = summary.regulatory_profile_id != null || summary.regulatory_profile_version != null;
  if (profileBound) {
    if (!summary.regulatory_profile_id || !summary.regulatory_profile_version) {
      context.addIssue({ code: z.ZodIssueCode.custom, path: ["regulatory_profile_id"], message: "Regulatory planning summary requires exact profile identity." });
    }
    const required = new Set(summary.regulatory_requirement_ids);
    if (
      summary.regulatory_requirements !== undefined &&
      (summary.regulatory_requirements.length !== required.size ||
        summary.regulatory_requirements.some((requirement) => !required.has(requirement.id)))
    ) {
      context.addIssue({ code: z.ZodIssueCode.custom, path: ["regulatory_requirements"], message: "Regulatory planning summary requires exact requirement definitions." });
    }
    const coverage = new Map(summary.regulatory_requirement_coverage.map((item) => [item.requirement_id, item]));
    if (!required.size || coverage.size !== required.size || [...required].some((id) => !coverage.has(id))) {
      context.addIssue({ code: z.ZodIssueCode.custom, path: ["regulatory_requirement_coverage"], message: "Regulatory planning summary requires exact coverage for every requirement." });
    } else {
      const coveredSourceFactIds = new Set([...coverage.values()].flatMap((item) => item.source_fact_ids));
      if (coveredSourceFactIds.size !== summary.regulatory_source_fact_ids.length || summary.regulatory_source_fact_ids.some((id) => !coveredSourceFactIds.has(id))) {
        context.addIssue({ code: z.ZodIssueCode.custom, path: ["regulatory_source_fact_ids"], message: "Regulatory planning summary requires exact covered source-fact IDs." });
      }
    }
  } else if (summary.regulatory_requirement_ids.length || (summary.regulatory_requirements?.length ?? 0) || summary.regulatory_source_fact_ids.length || summary.regulatory_requirement_coverage.length || summary.regulatory_review_candidates.length) {
    context.addIssue({ code: z.ZodIssueCode.custom, path: ["regulatory_requirement_coverage"], message: "Unprofiled planning summary cannot carry regulatory coverage." });
  }
});

export const ContentPlanningInputBlockerSchema = z.object({
  code: z.string().min(1),
  label: z.string().min(1),
  reason: z.string().min(1),
  next_step: z.string().min(1)
});

export const ContentPlanningInputReadinessResponseSchema = z.object({
  status: z.enum(["ready", "blocked"]),
  work_item_id: z.string().min(1).nullable().optional(),
  planning_input_digest: z.string().regex(/^[0-9a-f]{64}$/).nullable().optional(),
  input_summary: ContentPlanningInputSummarySchema.nullable().optional(),
  new_page_document_identity: ContentNewPageDocumentIdentitySchema.nullable().optional(),
  blockers: z.array(ContentPlanningInputBlockerSchema).default([]),
  safe_next_step: z.string().min(1)
}).superRefine((response, context) => {
  if (response.status === "ready" && (!response.work_item_id || !response.planning_input_digest || !response.input_summary)) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      message: "Ready planning input requires exact identity and summary."
    });
  }
  if (response.status === "blocked" && response.planning_input_digest) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      message: "Blocked planning input cannot expose a usable digest."
    });
  }
  if (response.input_summary?.goal === "new_page") {
    const identity = response.new_page_document_identity;
    if (response.status === "ready" && !identity) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Ready new-page planning input requires its exact document identity."
      });
    } else if (identity && (
      identity.work_item_id !== response.work_item_id ||
      identity.proposed_ia_location !== response.input_summary.proposed_ia_location
    )) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        message: "New-page document identity must match the ready planning input."
      });
    }
  } else if (response.new_page_document_identity) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      message: "Refresh planning cannot carry a new-page document identity."
    });
  }
});

export const ContentPlanningProposalResponseSchema = z.object({
  status: z.enum([
    "not_generated",
    "generating",
    "created",
    "idempotent",
    "ready",
    "stale",
    "blocked",
    "failed"
  ]),
  work_item_id: z.string().min(1),
  service_card_id: z.string().nullable().optional(),
  planning_input_digest: z.string().regex(/^[0-9a-f]{64}$/).nullable().optional(),
  input_summary: ContentPlanningInputSummarySchema.nullable().optional(),
  retry_after_seconds: z.number().int().nonnegative().nullable().optional(),
  proposal: ContentPlanningProposalSchema.nullable().optional(),
  planning_workspace: ContentPlanningWorkspaceSchema.nullable().optional(),
  runtime: ContentCodexRuntimeTraceSchema,
  blockers: z.array(ContentPlanningProposalBlockerSchema).default([]),
  safe_next_step: z.string().min(1),
  publish_ready: z.literal(false)
}).superRefine((response, context) => {
  if (response.planning_input_digest && !response.input_summary) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["input_summary"],
      message: "Planning input digest requires its exact input summary."
    });
  }
  if (response.proposal && (
    response.proposal.work_item_id !== response.work_item_id ||
    response.proposal.service_card_id !== response.service_card_id ||
    response.proposal.planning_input_digest !== response.planning_input_digest
  )) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["proposal"],
      message: "Planning response must match the nested exact proposal."
    });
  }
  if (["created", "idempotent", "ready"].includes(response.status) && response.proposal && response.input_summary?.regulatory_profile_id) {
    const coverage = new Map(response.input_summary.regulatory_requirement_coverage.map((item) => [item.requirement_id, new Set(item.evidence_ids)]));
    const required = new Set(response.input_summary.regulatory_requirement_ids);
    const sectionRequirements = new Set(response.proposal.sections.flatMap((section) => section.regulatory_requirement_ids));
    for (const requirementId of sectionRequirements) {
      if (!required.has(requirementId)) {
        context.addIssue({ code: z.ZodIssueCode.custom, path: ["proposal", "sections"], message: "Planning response cannot carry an unknown regulatory requirement." });
      }
    }
    for (const requirementId of required) {
      const sections = response.proposal.sections.filter((section) => section.regulatory_requirement_ids.includes(requirementId));
      if (!sections.length) {
        context.addIssue({ code: z.ZodIssueCode.custom, path: ["proposal", "sections"], message: "Planning response requires every regulatory requirement." });
      } else if (!sections.some((section) => section.evidence_ids.some((evidenceId) => coverage.get(requirementId)?.has(evidenceId)))) {
        context.addIssue({ code: z.ZodIssueCode.custom, path: ["proposal", "sections"], message: "Planning response requires exact regulatory evidence." });
      }
      const requirement = response.input_summary.regulatory_requirements?.find((item) => item.id === requirementId);
      if (requirement) {
        const sectionText = sections
          .map((section) => `${section.heading}\n${section.purpose}\n${section.reader_question}`)
          .join("\n")
          .replace(/\s+/g, " ")
          .toLocaleLowerCase("pl-PL");
        for (const assertion of requirement.document_assertions) {
          const covered = assertion.required_any_of.some((term) =>
            sectionText.includes(term.replace(/\s+/g, " ").toLocaleLowerCase("pl-PL"))
          );
          if (!covered) {
            context.addIssue({ code: z.ZodIssueCode.custom, path: ["proposal", "sections"], message: "Planning response omits a required regulatory document concept." });
          }
        }
      }
    }
  }
  if (response.planning_workspace) {
    if (response.status !== "ready" || !response.proposal) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["planning_workspace"],
        message: "Planning workspace is available only for a ready proposal."
      });
    } else if (
      JSON.stringify(response.planning_workspace.proposal) !== JSON.stringify(response.proposal)
    ) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["planning_workspace"],
        message: "Planning workspace must carry the response exact proposal."
      });
    }
  }
});

export const ContentNewPagePlanningProposalWorkspaceSchema = z.object({
  response_type: z.literal("content_new_page_planning_proposal_workspace"),
  contract_version: z.literal("content_new_page_planning_proposal_workspace_v1"),
  brief_id: z.string().min(1),
  readiness: ContentPlanningInputReadinessResponseSchema,
  proposal_status: ContentPlanningProposalResponseSchema.nullable().optional()
}).superRefine((workspace, context) => {
  const response = workspace.proposal_status;
  if (!response) return;
  const identity = workspace.readiness.new_page_document_identity;
  if (
    workspace.readiness.status !== "ready" ||
    !workspace.readiness.work_item_id ||
    !workspace.readiness.planning_input_digest ||
    !identity ||
    workspace.brief_id !== identity.brief_id ||
    response.work_item_id !== workspace.readiness.work_item_id ||
    response.service_card_id !== identity.service_card_id ||
    response.planning_input_digest !== workspace.readiness.planning_input_digest
  ) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      message: "New-page proposal workspace must keep one exact ready input."
    });
    return;
  }
  const proposal = response.proposal;
  const proposalIdentity = proposal?.new_page_document_identity;
  if (proposal && (
    proposal.goal !== "new_page" ||
    proposal.planning_input_digest !== workspace.readiness.planning_input_digest ||
    !proposalIdentity ||
    proposalIdentity.work_item_id !== identity.work_item_id ||
    proposalIdentity.brief_id !== identity.brief_id ||
    proposalIdentity.brief_digest !== identity.brief_digest ||
    proposalIdentity.foundation_id !== identity.foundation_id ||
    proposalIdentity.service_card_id !== identity.service_card_id ||
    proposalIdentity.service_card_digest !== identity.service_card_digest ||
    proposalIdentity.proposed_ia_location !== identity.proposed_ia_location
  )) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["proposal_status", "proposal"],
      message: "New-page proposal must match the workspace document identity."
    });
  }
});

export const ContentNewPageDocumentOutlineSectionSchema = z.object({
  section_id: z.string().min(1),
  heading: z.string().min(1),
  purpose: z.string().min(1)
});

export const ContentNewPageDocumentReviewPrerequisiteConflictSchema = z.object({
  response_type: z.literal("content_new_page_document_review_prerequisite_conflict"),
  contract_version: z.literal("content_new_page_document_review_prerequisite_conflict_v1"),
  status: z.literal("blocked"),
  code: z.literal("missing_planning_foundation"),
  brief_id: z.string().min(1),
  safe_next_step: z.string().min(1)
});

export const ContentNewPageCanonicalDocumentWorkspaceSchema = z.object({
  response_type: z.literal("content_new_page_canonical_document"),
  contract_version: z.literal("content_new_page_canonical_document_v3"),
  status: z.enum([
    "ready_for_document",
    "document_review_required",
    "document_approved",
    "document_needs_changes",
    "document_rejected",
    "document_deferred",
    "blocked"
  ]),
  work_item_id: z.string().min(1),
  brief_id: z.string().min(1),
  brief_digest: z.string().regex(/^[0-9a-f]{64}$/),
  foundation_id: z.string().min(1),
  service_card_id: z.string().min(1),
  service_card_digest: z.string().regex(/^[0-9a-f]{64}$/),
  proposal_id: z.string().trim().min(1).nullable().optional(),
  planning_digest: z.string().regex(/^[0-9a-f]{64}$/).nullable().optional(),
  planning_input_digest: z.string().regex(/^[0-9a-f]{64}$/).nullable().optional(),
  title: z.string().min(1),
  proposed_ia_location: z.string().trim().min(3),
  outline: z.array(ContentNewPageDocumentOutlineSectionSchema).default([]),
  document_status: z.enum([
    "not_created",
    "unreviewed",
    "approved",
    "needs_changes",
    "rejected",
    "deferred"
  ]),
  canonical_revision: ContentDraftRevisionSchema.nullable().optional(),
  revision_review: ContentDraftRevisionReviewSchema.nullable().optional(),
  assigned_source_material_ids: z.array(z.string()).default([]),
  assigned_knowledge_card_ids: z.array(z.string()).default([]),
  document_lineage: ContentDocumentWorkspaceDocumentLineageSchema.default({
    status: "not_recorded",
    source_material_ids: [],
    knowledge_cards: [],
    unresolved_knowledge_card_ids: [],
    reason: "Nie ma jeszcze zapisanej rewizji, więc WILQ nie może wskazać materiałów przypisanych do dokumentu."
  }),
  public_source_status: z.literal("not_applicable"),
  public_source_url: z.null(),
  public_deployment_status: z.literal("not_confirmed"),
  safe_next_step: z.string().min(1)
}).strict().superRefine((workspace, context) => {
  const revision = workspace.canonical_revision;
  if (!revision) {
    if (
      workspace.revision_review ||
      workspace.assigned_source_material_ids.length > 0 ||
      workspace.assigned_knowledge_card_ids.length > 0 ||
      workspace.document_status !== "not_created" ||
      workspace.document_lineage.status !== "not_recorded" ||
      workspace.document_lineage.source_material_ids.length > 0 ||
      workspace.document_lineage.knowledge_cards.length > 0 ||
      workspace.document_lineage.unresolved_knowledge_card_ids.length > 0
    ) {
      context.addIssue({ code: z.ZodIssueCode.custom, message: "Missing new-page revision cannot carry document lineage." });
    }
    if (
      workspace.status !== "ready_for_document" &&
      workspace.status !== "blocked"
    ) {
      context.addIssue({ code: z.ZodIssueCode.custom, message: "Document workspace status requires a canonical revision." });
    }
    const hasExactPlanIdentity = Boolean(
      workspace.proposal_id && workspace.planning_digest && workspace.planning_input_digest
    );
    if (workspace.status === "blocked") {
      if (
        workspace.proposal_id !== null ||
        workspace.planning_digest !== null ||
        workspace.planning_input_digest !== null
      ) {
        context.addIssue({ code: z.ZodIssueCode.custom, message: "Blocked new-page workspace cannot carry a current plan." });
      }
      return;
    }
    if (!hasExactPlanIdentity) {
      context.addIssue({ code: z.ZodIssueCode.custom, message: "New-page plan state requires exact proposal identity." });
    }
    if (workspace.status !== "ready_for_document") {
      context.addIssue({ code: z.ZodIssueCode.custom, message: "Generated new-page plan must be ready for its first document." });
    }
    return;
  }
  const identity = revision.new_page_document_identity;
  if (
    revision.document_kind !== "new_page" ||
    revision.final_canonical_url !== null ||
    !identity ||
    revision.work_item_id !== workspace.work_item_id ||
    revision.planning_digest !== workspace.planning_digest ||
    revision.planning_input_digest !== workspace.planning_input_digest ||
    identity.brief_id !== workspace.brief_id ||
    identity.brief_digest !== workspace.brief_digest ||
    identity.foundation_id !== workspace.foundation_id ||
    identity.service_card_id !== workspace.service_card_id ||
    identity.service_card_digest !== workspace.service_card_digest ||
    identity.proposed_ia_location !== workspace.proposed_ia_location
  ) {
    context.addIssue({ code: z.ZodIssueCode.custom, message: "Canonical revision does not match the exact new-page workspace." });
  }
  if (
    JSON.stringify(workspace.assigned_source_material_ids) !== JSON.stringify(revision.source_material_ids) ||
    JSON.stringify(workspace.assigned_knowledge_card_ids) !== JSON.stringify(revision.knowledge_card_ids)
  ) {
    context.addIssue({ code: z.ZodIssueCode.custom, message: "Workspace lineage must match the canonical new-page revision." });
  }
  const expectedSourceMaterialIds = [...new Set(revision.source_material_ids)];
  const expectedKnowledgeCardIds = [...new Set(revision.knowledge_card_ids)];
  const lineageKnowledgeCardIds = workspace.document_lineage.knowledge_cards.map((card) => card.id);
  if (
    JSON.stringify(workspace.document_lineage.source_material_ids) !== JSON.stringify(expectedSourceMaterialIds) ||
    new Set([...lineageKnowledgeCardIds, ...workspace.document_lineage.unresolved_knowledge_card_ids]).size !== expectedKnowledgeCardIds.length ||
    !expectedKnowledgeCardIds.every((id) =>
      lineageKnowledgeCardIds.includes(id) || workspace.document_lineage.unresolved_knowledge_card_ids.includes(id)
    ) ||
    new Set(lineageKnowledgeCardIds).size !== lineageKnowledgeCardIds.length
  ) {
    context.addIssue({ code: z.ZodIssueCode.custom, message: "Document lineage must match the canonical new-page revision." });
  }
  const expectedLineageStatus = expectedSourceMaterialIds.length === 0 && expectedKnowledgeCardIds.length === 0
    ? "not_recorded"
    : workspace.document_lineage.unresolved_knowledge_card_ids.length > 0
      ? "partial"
      : "available";
  if (workspace.document_lineage.status !== expectedLineageStatus) {
    context.addIssue({ code: z.ZodIssueCode.custom, message: "Document lineage status must match the canonical revision." });
  }
  const review = workspace.revision_review;
  const expectedStatus = review ? review.decision : "unreviewed";
  if (
    workspace.document_status !== expectedStatus ||
    (review && (review.revision_id !== revision.revision_id || review.revision_digest !== revision.content_digest))
  ) {
    context.addIssue({ code: z.ZodIssueCode.custom, message: "Workspace review must match the canonical revision and status." });
  }
  if (workspace.document_status === "not_created") {
    context.addIssue({ code: z.ZodIssueCode.custom, message: "Canonical new-page revision requires a document status." });
    return;
  }
  const expectedWorkspaceStatus = {
    unreviewed: "document_review_required",
    approved: "document_approved",
    needs_changes: "document_needs_changes",
    rejected: "document_rejected",
    deferred: "document_deferred"
  }[workspace.document_status];
  if (workspace.status !== expectedWorkspaceStatus) {
    context.addIssue({ code: z.ZodIssueCode.custom, message: "Workspace status must match the canonical document status." });
  }
});

/** Typed 409 body for an exact new-page revision-review conflict. */
export const ContentNewPageRevisionReviewConflictSchema = z.union([
  ContentDraftRevisionConflictSchema,
  ContentNewPageDocumentReviewPrerequisiteConflictSchema
]);

export const ContentNewPageRevisionReviewResponseSchema = z.object({
  status: z.enum(["recorded", "idempotent"]),
  review: ContentDraftRevisionReviewSchema
});

export const ContentInitialDraftRequestSchema = z.object({
  expected_proposal_id: z.string().min(1),
  expected_planning_digest: z.string().regex(/^[0-9a-f]{64}$/),
  expected_planning_input_digest: z.string().regex(/^[0-9a-f]{64}$/),
  requested_by: z.string().min(1)
});

export const ContentInitialDraftBlockerSchema = z.object({
  code: z.string().min(1),
  label: z.string().min(1),
  reason: z.string().min(1),
  next_step: z.string().min(1),
  source_codes: z.array(z.string()).default([])
});

export const ContentInitialDraftResponseSchema = z.object({
  status: z.enum(["generating", "created", "blocked", "failed", "conflict"]),
  work_item_id: z.string().min(1),
  proposal_id: z.string().nullable().optional(),
  run_id: z.string().nullable().optional(),
  revision: ContentDraftRevisionSchema.nullable().optional(),
  runtime: ContentCodexRuntimeTraceSchema,
  blockers: z.array(ContentInitialDraftBlockerSchema).default([]),
  safe_next_step: z.string().min(1),
  publish_ready: z.literal(false)
}).superRefine((response, context) => {
  if (response.status === "created") {
    if (!response.revision || !response.run_id || response.blockers.length > 0) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        message: "created initial draft requires revision and run without blockers"
      });
    }
  } else if (response.status === "generating") {
    if (response.revision || response.blockers.length === 0) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        message: "generating initial draft requires blockers without revision"
      });
    }
  } else if (response.revision || response.blockers.length === 0) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      message: "non-created initial draft requires blockers without revision"
    });
  }
});

export const ContentSemanticDimensionSchema = z.enum([
  "answer_directness",
  "completeness",
  "logical_flow",
  "specificity",
  "repetition",
  "search_intent_fit",
  "buyer_fit",
  "credibility",
  "conversion_clarity"
]);

export const ContentSemanticDimensionAssessmentSchema = z.object({
  dimension: ContentSemanticDimensionSchema,
  status: z.enum(["strong", "needs_changes"]),
  reason: z.string().min(1),
  affected_targets: z.array(z.string().min(1)).min(1)
});

export const ContentSemanticFindingSchema = z.object({
  finding_id: z.string().min(1),
  dimension: ContentSemanticDimensionSchema,
  severity: z.enum(["high", "medium", "low"]),
  label: z.string().min(1),
  reason: z.string().min(1),
  instruction: z.string().min(1),
  affected_targets: z.array(z.string().min(1)).min(1),
  evidence_ids: z.array(z.string()).default([])
});

export const ContentSemanticReviewSchema = z.object({
  review_id: z.string().min(1),
  work_item_id: z.string().min(1),
  revision_id: z.string().min(1),
  revision_digest: z.string().regex(/^[0-9a-f]{64}$/),
  criteria_version: z.literal("wilq_semantic_content_review_v1"),
  codex_run_id: z.string().min(1),
  status: z.enum(["reviewable", "needs_changes"]),
  dimensions: z.array(ContentSemanticDimensionAssessmentSchema).length(9),
  findings: z.array(ContentSemanticFindingSchema).default([]),
  evidence_ids: z.array(z.string()).default([]),
  source_connectors: z.array(z.string()).default([]),
  requested_by: z.string().min(1),
  created_at: z.string().min(1),
  safe_next_step: z.string().min(1),
  publish_ready: z.literal(false),
  human_review_required: z.literal(true),
  action_object_created: z.literal(false)
}).superRefine((review, context) => {
  const expectedDimensions = ContentSemanticDimensionSchema.options;
  if (
    review.dimensions.some(
      (assessment, index) => assessment.dimension !== expectedDimensions[index]
    )
  ) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["dimensions"],
      message: "semantic review must assess every dimension in canonical order"
    });
  }
  const findingIds = review.findings.map((finding) => finding.finding_id);
  if (new Set(findingIds).size !== findingIds.length) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["findings"],
      message: "semantic finding IDs must be unique"
    });
  }
  const findingDimensions = new Set(review.findings.map((finding) => finding.dimension));
  const needsChangeDimensions = new Set(
    review.dimensions
      .filter((assessment) => assessment.status === "needs_changes")
      .map((assessment) => assessment.dimension)
  );
  if (
    findingDimensions.size !== needsChangeDimensions.size ||
    [...findingDimensions].some((dimension) => !needsChangeDimensions.has(dimension))
  ) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["findings"],
      message: "semantic findings must match needs-change dimensions"
    });
  }
  if ((review.findings.length > 0) !== (review.status === "needs_changes")) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      message: "semantic review status must be derived from findings"
    });
  }
});

export const ContentSemanticReviewRequestSchema = z.object({
  expected_revision_digest: z.string().regex(/^[0-9a-f]{64}$/),
  requested_by: z.string().min(1)
});

export const ContentSemanticReviewBlockerCodeSchema = z.enum([
  "missing_revision",
  "stale_revision",
  "legacy_revision",
  "stale_content_context",
  "missing_planning_input",
  "source_material_review_required",
  "storage_activation_required",
  "runtime_blocked",
  "runtime_failed",
  "invalid_structured_output",
  "semantic_scope_mismatch",
  "persistence_failed",
  "review_conflict",
  "generation_in_progress"
]);

export const ContentSemanticReviewBlockerSchema = z.object({
  code: ContentSemanticReviewBlockerCodeSchema,
  label: z.string().min(1),
  reason: z.string().min(1),
  next_step: z.string().min(1),
  source_codes: z.array(z.string()).default([])
});

export const ContentSemanticReviewResponseSchema = z.object({
  status: z.enum([
    "generating",
    "not_generated",
    "created",
    "idempotent",
    "ready",
    "stale",
    "blocked",
    "failed",
    "conflict"
  ]),
  work_item_id: z.string().min(1),
  revision_id: z.string().nullable().optional(),
  revision_digest: z.string().regex(/^[0-9a-f]{64}$/).nullable().optional(),
  review: ContentSemanticReviewSchema.nullable().optional(),
  run_id: z.string().nullable().optional(),
  runtime: ContentCodexRuntimeTraceSchema,
  blockers: z.array(ContentSemanticReviewBlockerSchema).default([]),
  safe_next_step: z.string().min(1),
  publish_ready: z.literal(false),
  human_review_required: z.literal(true),
  action_object_created: z.literal(false)
}).superRefine((response, context) => {
  const readable = ["created", "idempotent", "ready", "stale"].includes(response.status);
  if (readable && (!response.review || response.blockers.length > 0)) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      message: "readable semantic review requires a result without blockers"
    });
  } else if (response.status === "not_generated") {
    if (response.review || response.blockers.length > 0) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        message: "not-generated semantic review cannot expose result or blockers"
      });
    }
  } else if (!readable && (response.review || response.blockers.length === 0)) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      message: "blocked semantic review requires blockers without a result"
    });
  }
  if (
    response.review &&
    (response.work_item_id !== response.review.work_item_id ||
      response.revision_id !== response.review.revision_id ||
      response.revision_digest !== response.review.revision_digest ||
      response.run_id !== response.review.codex_run_id)
  ) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["review"],
      message: "semantic response must bind the exact embedded review"
    });
  }
});

export const ContentWorkItemWorkflowSnapshotResponseSchema = z.object({
  response_type: z.literal("workflow_snapshot").default("workflow_snapshot"),
  freshness_assessment: ContentFreshnessAssessmentSchema,
  candidate: ContentWorkItemQueueCandidateSchema,
  service_profile_context: ContentWorkItemServiceProfileContextSchema.default(
    ContentWorkItemServiceProfileContextDefault
  ),
  claim_ledger: ContentClaimLedgerSchema,
  preflight: ContentWorkItemPreflightResponseSchema,
  sales_brief: ContentWorkItemSalesBriefResponseSchema,
  draft_package: ContentWorkItemDraftPackageResponseSchema,
  structured_generation_readiness: ContentStructuredGenerationBrowserReadinessSchema,
  human_review: ContentWorkItemHumanReviewResponseSchema,
  wordpress_handoff: ContentWorkItemWordPressDraftHandoffResponseSchema,
  measurement_window: ContentWorkItemMeasurementWindowResponseSchema,
  revision_workspace: ContentDraftRevisionWorkspaceSchema,
  planning_workspace: ContentPlanningWorkspaceSchema.nullable().optional(),
  current_step_id: ContentWorkflowOperatorStepIdSchema,
  operator_steps: z.array(ContentWorkflowOperatorStepSchema).length(5)
}).superRefine((snapshot, context) => {
  const stepIds = snapshot.operator_steps.map((step) => step.id);
  if (new Set(stepIds).size !== stepIds.length) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["operator_steps"],
      message: "operator_steps must contain five unique step IDs"
    });
  }
  if (
    stepIds.some(
      (stepId, index) => stepId !== CONTENT_WORKFLOW_OPERATOR_STEP_ORDER[index]
    )
  ) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["operator_steps"],
      message: "operator_steps must use the canonical five-step order"
    });
  }
  const currentSteps = snapshot.operator_steps.filter((step) => step.phase === "current");
  if (
    currentSteps.length !== 1 ||
    currentSteps[0]?.id !== snapshot.current_step_id
  ) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["current_step_id"],
      message: "current_step_id must identify the single current operator step"
    });
  }
});

export const ContentWorkItemBlockedSnapshotResponseSchema = z.object({
  response_type: z.literal("blocked_snapshot"),
  work_item_id: z.string(),
  decision_id: z.string(),
  freshness_assessment: ContentFreshnessAssessmentSchema,
  title: z.string(),
  topic: z.string(),
  status_label: z.string(),
  reason: z.string(),
  safe_next_step: z.string(),
  recommended_mode: z.string(),
  preflight_status: z.string(),
  blockers: z.array(ContentWorkItemQueueBlockerSchema).default([]),
  ...ContentEvidenceTraceFields,
  candidate: ContentWorkItemQueueCandidateSchema,
  service_profile_context: ContentWorkItemServiceProfileContextSchema.default(
    ContentWorkItemServiceProfileContextDefault
  )
});

export const ContentWorkItemSnapshotResponseSchema = z.discriminatedUnion(
  "response_type",
  [
    ContentWorkItemWorkflowSnapshotResponseSchema,
    ContentWorkItemBlockedSnapshotResponseSchema
  ]
);

export const ContentOpportunityEnrichmentBlockerSchema = z.object({
  code: z.string(),
  label: z.string(),
  reason: z.string(),
  next_step: z.string(),
  ...ContentEvidenceTraceFields
});

export const ContentOpportunitySourceFactSchema = z.object({
  id: z.string(),
  signal_kind: z.enum([
    "gsc_query",
    "gsc_page",
    "ga4_behavior",
    "ahrefs_gap",
    "ads_search_term",
    "merchant_service_signal",
    "wordpress_inventory",
    "measurement"
  ]),
  label: z.string(),
  summary: z.string(),
  ...ContentEvidenceTraceFields,
  metric_value: z.union([z.number(), z.string()]).nullable().optional(),
  source_url: z.string().nullable().optional()
});

export const ContentOpportunityMeasurementBaselineSchema = z.object({
  status: z.enum(["ready_to_plan", "blocked"]),
  label: z.string(),
  reason: z.string(),
  metrics_to_watch: z.array(z.string()).default([]),
  ...ContentEvidenceTraceFields
});

export const ContentOpportunityEnrichmentSchema = z.object({
  id: z.string(),
  work_item_id: z.string(),
  decision_id: z.string(),
  status: z.enum(["ready", "blocked"]),
  status_label: z.string(),
  title: z.string(),
  topic: z.string(),
  recommended_mode: ContentRecommendedModeSchema,
  recommended_mode_label: z.string(),
  intent: z.enum([
    "informational_service",
    "service_comparison",
    "compliance_risk",
    "measurement_fix",
    "gap_review",
    "unknown"
  ]),
  intent_label: z.string(),
  buyer_problem: z.string(),
  buyer_trigger: z.string(),
  service_fit: z.string(),
  cta_hypothesis: z.string(),
  source_facts: z.array(ContentOpportunitySourceFactSchema).default([]),
  measurement_baseline: ContentOpportunityMeasurementBaselineSchema,
  blockers: z.array(ContentOpportunityEnrichmentBlockerSchema).default([]),
  ...ContentEvidenceTraceFields,
  ...ContentSafeNextStepField
});

export const ContentOpportunityEnrichmentResponseSchema = z.object({
  enrichment: ContentOpportunityEnrichmentSchema.nullable().optional(),
  blockers: z.array(ContentOpportunityEnrichmentBlockerSchema).default([])
});

export const ContentInventoryCatalogItemSchema = z.object({
  catalog_id: z.string(),
  work_item_id: z.string(),
  url: z.string(),
  path: z.string(),
  title: z.string().nullable(),
  content_type: z.string(),
  content_summary: z.string().nullable(),
  content_word_count: z.number().int().nonnegative().nullable(),
  section_count: z.number().int().nonnegative().nullable(),
  acf_section_count: z.number().int().nonnegative().nullable(),
  acf_field_names: z.array(z.string()).default([]),
  acf_section_headings: z.array(z.string()).default([]),
  material_status: z.enum([
    "content_and_structure",
    "content_summary",
    "structure_only",
    "url_only"
  ]),
  source_connector: z.string(),
  evidence_id: z.string(),
  collected_at: z.string(),
  metrics_status: z.enum(["available", "missing"]).default("missing"),
  metrics_evidence_ids: z.array(z.string()).default([]),
  metrics_query_count: z.number().int().nonnegative().default(0),
  metrics_clicks: z.number().int().nonnegative().default(0),
  metrics_impressions: z.number().int().nonnegative().default(0)
});

export const ContentInventoryCatalogResponseSchema = z.object({
  status: z.enum(["ready", "blocked"]),
  total_count: z.number().int().nonnegative(),
  ready_count: z.number().int().nonnegative().default(0),
  partial_count: z.number().int().nonnegative().default(0),
  blocked_count: z.number().int().nonnegative().default(0),
  items: z.array(ContentInventoryCatalogItemSchema),
  source_connectors: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()).default([]),
  coverage: z.object({
    status: z.string(),
    source_count: z.number().int().nonnegative().nullable().optional(),
    returned_count: z.number().int().nonnegative(),
    public_sitemap_source_count: z.number().int().nonnegative().nullable().optional(),
    public_sitemap_returned_count: z.number().int().nonnegative().nullable().optional(),
    public_sitemap_limit: z.number().int().nonnegative().nullable().optional(),
    public_sitemap_truncated: z.boolean().nullable().optional(),
    limit: z.number().int().nonnegative().nullable().optional(),
    truncated: z.boolean().nullable().optional(),
    caveat: z.string()
  }).default({
    status: "unknown",
    returned_count: 0,
    caveat: "Brak coverage z aktualnego odczytu WordPress."
  })
});

export const ContentInventoryMaterialResponseSchema = z.object({
  status: z.enum(["ready", "blocked"]),
  url: z.string(),
  source_kind: z.string().nullable().optional(),
  title: z.string().nullable().optional(),
  content_text: z.string().nullable().optional(),
  content_summary: z.string().nullable().optional(),
  content_word_count: z.number().int().nonnegative().nullable().optional(),
  section_headings: z.array(z.string()).default([]),
  acf_field_names: z.array(z.string()).default([]),
  acf_section_headings: z.array(z.string()).default([]),
  modified_gmt: z.string().nullable().optional(),
  evidence_id: z.string().nullable().optional(),
  blocker_code: z.string().nullable().optional(),
  blocker: z.string().nullable().optional(),
  extraction_region: z.string().nullable().optional(),
  material_confidence: z.string().nullable().optional(),
  source_field_lineage: z.array(z.string()).default([])
});

export const ContentInventoryBindingRequestSchema = z.object({ url: z.string().min(1) });
export const ContentInventoryBindingResponseSchema = z.object({
  status: z.enum(["ready", "blocked"]),
  url: z.string(),
  work_item_id: z.string().nullable().optional(),
  title: z.string().nullable().optional(),
  evidence_id: z.string().nullable().optional(),
  material_status: z.string().nullable().optional(),
  material_source_kind: z.string().nullable().optional(),
  material_confidence: z.string().nullable().optional(),
  extraction_region: z.string().nullable().optional(),
  source_field_lineage: z.array(z.string()).default([]),
  blocker_code: z.string().nullable().optional(),
  blocker: z.string().nullable().optional(),
  metrics_status: z.string().default("not_evaluated"),
  metrics_evidence_ids: z.array(z.string()).default([]),
  knowledge_status: z.string().default("not_evaluated"),
  generation_status: z.string().default("blocked_until_service_and_metrics")
});

export type ContentWorkItem = z.infer<typeof ContentWorkItemSchema>;
export type ContentWorkItemQueueCandidate = z.infer<
  typeof ContentWorkItemQueueCandidateSchema
>;
export type ContentWorkItemQueueResponse = z.infer<typeof ContentWorkItemQueueResponseSchema>;
export type ContentDecisionContext = z.infer<typeof ContentDecisionContextSchema>;
export type ContentDocumentWorkspace = z.infer<typeof ContentDocumentWorkspaceSchema>;
export type ContentSelectedWorkspace = z.infer<typeof ContentSelectedWorkspaceSchema>;
export type ContentTargetDiscovery = z.infer<typeof ContentTargetDiscoverySchema>;
export type ContentTargetMappingPreview = z.infer<typeof ContentTargetMappingPreviewSchema>;
export type ContentTargetMappingConfirmation = z.infer<
  typeof ContentTargetMappingConfirmationSchema
>;
export type ContentTargetMappingConfirmationCommand = z.input<
  typeof ContentTargetMappingConfirmationCommandSchema
>;
export type ContentTargetMappingConfirmationResult = z.infer<
  typeof ContentTargetMappingConfirmationResultSchema
>;
export type ContentTargetDraftPreview = z.infer<typeof ContentTargetDraftPreviewSchema>;
export type ContentTargetDraftActionCommand = z.infer<typeof ContentTargetDraftActionCommandSchema>;
export type ContentNewPageDeliveryReadiness = z.infer<typeof ContentNewPageDeliveryReadinessSchema>;
export type ContentNewPageDraftActionCommand = z.input<typeof ContentNewPageDraftActionCommandSchema>;
export type ContentWorkflowEntryResponse = z.infer<typeof ContentWorkflowEntryResponseSchema>;
export type ContentNewPageBriefInput = z.input<typeof ContentNewPageBriefInputSchema>;
export type ContentNewPageTopicCandidate = z.infer<typeof ContentNewPageTopicCandidateSchema>;
export type ContentNewPageTopicRecommendations = z.infer<
  typeof ContentNewPageTopicRecommendationsSchema
>;
export type ContentNewPageBriefWorkspace = z.infer<typeof ContentNewPageBriefWorkspaceSchema>;
export type ContentNewPageFoundationCommand = z.input<typeof ContentNewPageFoundationCommandSchema>;
export type ContentNewPageFoundationResult = z.infer<typeof ContentNewPageFoundationResultSchema>;
export type ContentInventoryCatalogItem = z.infer<typeof ContentInventoryCatalogItemSchema>;
export type ContentInventoryCatalogResponse = z.infer<typeof ContentInventoryCatalogResponseSchema>;
export type ContentInventoryMaterialResponse = z.infer<typeof ContentInventoryMaterialResponseSchema>;
export type ContentInventoryBindingRequest = z.input<typeof ContentInventoryBindingRequestSchema>;
export type ContentInventoryBindingResponse = z.infer<typeof ContentInventoryBindingResponseSchema>;
export type ContentWorkItemPreflightResponse = z.infer<
  typeof ContentWorkItemPreflightResponseSchema
>;
export type ContentWorkItemPreflightRequest = z.input<
  typeof ContentWorkItemPreflightRequestSchema
>;
export type ContentClaimLedger = z.infer<typeof ContentClaimLedgerSchema>;
export type ContentWorkItemSalesBriefResponse = z.infer<
  typeof ContentWorkItemSalesBriefResponseSchema
>;
export type ContentWorkItemSalesBriefRequest = z.input<
  typeof ContentWorkItemSalesBriefRequestSchema
>;
export type ContentKnowledgeCard = z.infer<typeof ContentKnowledgeCardSchema>;
export type KnowledgeSourceFactView = z.infer<typeof KnowledgeSourceFactViewSchema>;
export type KnowledgeSourceMaterialView = z.infer<typeof KnowledgeSourceMaterialViewSchema>;
export type KnowledgeSourceMaterialReadiness = z.infer<
  typeof KnowledgeSourceMaterialReadinessSchema
>;
export type ContentKnowledgeProductionDepthReadiness = z.infer<
  typeof ContentKnowledgeProductionDepthReadinessSchema
>;
export type ContentKnowledgeCardsResponse = z.infer<
  typeof ContentKnowledgeCardsResponseSchema
>;
export type ContentServiceProfileResponse = z.infer<
  typeof ContentServiceProfileResponseSchema
>;
export type ContentWorkItemDraftPackageResponse = z.infer<
  typeof ContentWorkItemDraftPackageResponseSchema
>;
export type ContentWorkItemDraftPackageRequest = z.input<
  typeof ContentWorkItemDraftPackageRequestSchema
>;
export type ContentStructuredGenerationBrowserReadiness = z.infer<
  typeof ContentStructuredGenerationBrowserReadinessSchema
>;
export type ContentQualityReview = z.infer<typeof ContentQualityReviewSchema>;
export type ContentRevisionPlan = z.infer<typeof ContentRevisionPlanSchema>;
export type ContentWorkItemQualityReviewRequest = z.input<
  typeof ContentWorkItemQualityReviewRequestSchema
>;
export type ContentWorkItemQualityReviewResponse = z.infer<
  typeof ContentWorkItemQualityReviewResponseSchema
>;
export type ContentWorkItemHumanReviewResponse = z.infer<
  typeof ContentWorkItemHumanReviewResponseSchema
>;
export type ContentWorkItemHumanReviewRequest = z.input<
  typeof ContentWorkItemHumanReviewRequestSchema
>;
export type ContentWorkItemSnapshotHumanReviewRequest = z.input<
  typeof ContentWorkItemSnapshotHumanReviewRequestSchema
>;
export type ContentWorkItemSnapshotAuditRequest = z.input<
  typeof ContentWorkItemSnapshotAuditRequestSchema
>;
export type ContentWorkItemWordPressDraftHandoffResponse = z.infer<
  typeof ContentWorkItemWordPressDraftHandoffResponseSchema
>;
export type ContentWorkItemWordPressDraftHandoffRequest = z.input<
  typeof ContentWorkItemWordPressDraftHandoffRequestSchema
>;
export type ContentWorkItemWordPressDraftExecutionRequest = z.input<
  typeof ContentWorkItemWordPressDraftExecutionRequestSchema
>;
export type ContentWorkItemWordPressDraftExecutionResponse = z.infer<
  typeof ContentWorkItemWordPressDraftExecutionResponseSchema
>;
export type ContentWordPressDraftSectionOverride = z.input<
  typeof ContentWordPressDraftSectionOverrideSchema
>;
export type ContentWordPressDraftWriteReadinessResponse = z.infer<
  typeof ContentWordPressDraftWriteReadinessResponseSchema
>;
export type ContentWordPressExistingDraftUpdateReadinessResponse = z.infer<
  typeof ContentWordPressExistingDraftUpdateReadinessResponseSchema
>;
export type ContentWordPressDraftActivationPacketResponse = z.infer<
  typeof ContentWordPressDraftActivationPacketResponseSchema
>;
export type ContentWorkItemMeasurementWindowResponse = z.infer<
  typeof ContentWorkItemMeasurementWindowResponseSchema
>;
export type ContentPublicDeployment = z.infer<typeof ContentPublicDeploymentSchema>;
export type ContentPublicDeploymentConfirmationResponse = z.infer<
  typeof ContentPublicDeploymentConfirmationResponseSchema
>;
export type ContentPublicDeploymentConfirmationCommand = z.input<
  typeof ContentPublicDeploymentConfirmationCommandSchema
>;
export type ContentPublicDeploymentObservation = z.infer<
  typeof ContentPublicDeploymentObservationSchema
>;
export type ContentPublicDeploymentReadResponse = z.infer<
  typeof ContentPublicDeploymentReadResponseSchema
>;
export type ContentWorkItemMeasurementWindowRequest = z.input<
  typeof ContentWorkItemMeasurementWindowRequestSchema
>;
export type ContentMeasurementOutcomeInterpretation = z.infer<
  typeof ContentMeasurementOutcomeInterpretationSchema
>;
export type ContentWorkItemMeasurementOutcomeRequest = z.input<
  typeof ContentWorkItemMeasurementOutcomeRequestSchema
>;
export type ContentWorkItemMeasurementOutcomeResponse = z.infer<
  typeof ContentWorkItemMeasurementOutcomeResponseSchema
>;
export type ContentLearningProposal = z.infer<typeof ContentLearningProposalSchema>;
export type ContentWorkItemLearningProposalRequest = z.input<
  typeof ContentWorkItemLearningProposalRequestSchema
>;
export type ContentWorkItemLearningProposalResponse = z.infer<
  typeof ContentWorkItemLearningProposalResponseSchema
>;
export type ContentDraftRevisionSection = z.infer<typeof ContentDraftRevisionSectionSchema>;
export type ContentDraftRevisionProposalSectionLineage = z.infer<
  typeof ContentDraftRevisionProposalSectionLineageSchema
>;
export type ContentDraftRevisionProposalMetadata = z.infer<
  typeof ContentDraftRevisionProposalMetadataSchema
>;
export type ContentDraftRevision = z.infer<typeof ContentDraftRevisionSchema>;
export type ContentDraftRevisionDecision = z.infer<typeof ContentDraftRevisionDecisionSchema>;
export type ContentDraftRevisionReview = z.infer<typeof ContentDraftRevisionReviewSchema>;
export type ContentDraftRevisionWorkspace = z.infer<typeof ContentDraftRevisionWorkspaceSchema>;
export type ContentDraftRevisionSaveRequest = z.input<
  typeof ContentDraftRevisionSaveRequestSchema
>;
export type ContentDraftRevisionSaveResponse = z.infer<
  typeof ContentDraftRevisionSaveResponseSchema
>;
export type ContentOfficialSourceLineageRebaseRequest = z.input<
  typeof ContentOfficialSourceLineageRebaseRequestSchema
>;
export type ContentDraftRevisionReviewRequest = z.input<
  typeof ContentDraftRevisionReviewRequestSchema
>;
export type ContentDraftRevisionReviewResponse = z.infer<
  typeof ContentDraftRevisionReviewResponseSchema
>;
export type ContentRevisionHtmlPackageManifest = z.infer<
  typeof ContentRevisionHtmlPackageManifestSchema
>;
export type ContentRevisionHtmlPackageResponse = z.infer<
  typeof ContentRevisionHtmlPackageResponseSchema
>;
export type ContentEditorialIntegrityReport = z.infer<
  typeof ContentEditorialIntegrityReportSchema
>;
export type ContentDraftRevisionConflict = z.infer<
  typeof ContentDraftRevisionConflictSchema
>;
export type ContentWorkflowOperatorStep = z.infer<typeof ContentWorkflowOperatorStepSchema>;
export type ContentWorkflowOperatorJourney = z.infer<
  typeof ContentWorkflowOperatorJourneySchema
>;
export type ContentPlanningWorkspace = z.infer<typeof ContentPlanningWorkspaceSchema>;
export type ContentPlanningProposal = z.infer<typeof ContentPlanningProposalSchema>;
export type ContentRegulatorySourceReviewCommand = z.input<
  typeof ContentRegulatorySourceReviewCommandSchema
>;
export type ContentRegulatorySourceReview = z.infer<
  typeof ContentRegulatorySourceReviewSchema
>;
export type ContentRegulatorySourceReviewList = z.infer<
  typeof ContentRegulatorySourceReviewListSchema
>;
export type ContentRegulatorySourceReviewConflict = z.infer<
  typeof ContentRegulatorySourceReviewConflictSchema
>;
export type ContentRegulatorySourceSnapshot = z.infer<
  typeof ContentRegulatorySourceSnapshotSchema
>;
export type ContentRegulatorySourceSnapshotReadResponse = z.infer<
  typeof ContentRegulatorySourceSnapshotReadResponseSchema
>;
export type ContentRegulatorySourceFactProposal = z.infer<
  typeof ContentRegulatorySourceFactProposalSchema
>;
export type ContentRegulatorySourceFactProposalResponse = z.infer<
  typeof ContentRegulatorySourceFactProposalResponseSchema
>;
export type ContentRegulatorySourceFactProposalReviewCommand = z.input<
  typeof ContentRegulatorySourceFactProposalReviewCommandSchema
>;
export type ContentPlanningInputReadinessResponse = z.infer<
  typeof ContentPlanningInputReadinessResponseSchema
>;
export type ContentNewPageDocumentIdentity = z.infer<
  typeof ContentNewPageDocumentIdentitySchema
>;
export type ContentNewPagePlanningProposalRequest = z.input<
  typeof ContentNewPagePlanningProposalRequestSchema
>;
export type ContentNewPageCanonicalDocumentWorkspace = z.infer<
  typeof ContentNewPageCanonicalDocumentWorkspaceSchema
>;
export type ContentNewPageDocumentReviewPrerequisiteConflict = z.infer<
  typeof ContentNewPageDocumentReviewPrerequisiteConflictSchema
>;
export type ContentNewPagePlanningProposalWorkspace = z.infer<
  typeof ContentNewPagePlanningProposalWorkspaceSchema
>;
export type ContentNewPageRevisionReviewConflict = z.infer<
  typeof ContentNewPageRevisionReviewConflictSchema
>;
export type ContentNewPageRevisionReviewResponse = z.infer<
  typeof ContentNewPageRevisionReviewResponseSchema
>;
export type ContentPlanningProposalRequest = z.input<
  typeof ContentPlanningProposalRequestSchema
>;
export type ContentPlanningProposalResponse = z.infer<
  typeof ContentPlanningProposalResponseSchema
>;
export type ContentInitialDraftRequest = z.input<typeof ContentInitialDraftRequestSchema>;
export type ContentInitialDraftResponse = z.infer<typeof ContentInitialDraftResponseSchema>;
export type ContentRevisionRepairProposalRequest = z.input<
  typeof ContentRevisionRepairProposalRequestSchema
>;
export type ContentRevisionRepairProposalResponse = z.infer<
  typeof ContentRevisionRepairProposalResponseSchema
>;
export type ContentSemanticReview = z.infer<typeof ContentSemanticReviewSchema>;
export type ContentSemanticReviewRequest = z.input<typeof ContentSemanticReviewRequestSchema>;
export type ContentSemanticReviewResponse = z.infer<typeof ContentSemanticReviewResponseSchema>;
export type ContentWorkItemServiceProfileContext = z.infer<
  typeof ContentWorkItemServiceProfileContextSchema
>;
export type ContentWorkItemServiceCandidate = z.infer<
  typeof ContentWorkItemServiceCandidateSchema
>;
export type ContentWorkItemWorkflowSnapshotResponse = z.infer<
  typeof ContentWorkItemWorkflowSnapshotResponseSchema
>;
export type ContentFreshnessAssessment = z.infer<typeof ContentFreshnessAssessmentSchema>;
export type ContentWorkItemBlockedSnapshotResponse = z.infer<
  typeof ContentWorkItemBlockedSnapshotResponseSchema
>;
export type ContentWorkItemSnapshotResponse = z.infer<
  typeof ContentWorkItemSnapshotResponseSchema
>;
export type ContentOpportunityEnrichment = z.infer<
  typeof ContentOpportunityEnrichmentSchema
>;
export type ContentOpportunityEnrichmentResponse = z.infer<
  typeof ContentOpportunityEnrichmentResponseSchema
>;
export type ContentOperatorContext = z.infer<typeof ContentOperatorContextSchema>;
