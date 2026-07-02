import { z } from "zod";

export const ContentInventoryStatusSchema = z.enum(["missing", "resolved", "blocked"]);
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

export const ContentWorkItemSchema = z.object({
  id: z.string(),
  topic: z.string(),
  source_public_url: z.string().nullable().optional(),
  final_canonical_url: z.string().nullable().optional(),
  intended_final_url: z.string().nullable().optional(),
  preview_url: z.string().nullable().optional(),
  evidence_ids: z.array(z.string()).default([]),
  source_connectors: z.array(z.string()).default([]),
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

export const ContentWorkItemQueueCandidateSchema = z.object({
  work_item_id: z.string(),
  decision_id: z.string(),
  title: z.string(),
  topic: z.string(),
  priority: z.number(),
  recommended_mode: z.enum(["preserve", "refresh", "merge", "create", "block"]),
  recommended_mode_label: z.string(),
  status_label: z.string(),
  reason: z.string(),
  ...ContentEvidenceTraceFields,
  source_connector_labels: z.array(z.string()).default([]),
  source_public_url: z.string().nullable().optional(),
  final_canonical_url: z.string().nullable().optional(),
  intended_final_url: z.string().nullable().optional(),
  preview_url: z.string().nullable().optional(),
  preflight_status: z.string(),
  preflight_status_label: z.string(),
  duplicate_canonical_risk_summary: z.string(),
  measurement_readiness: ContentWorkItemQueueMeasurementReadinessSchema,
  safe_next_step: z.string(),
  blockers: z.array(ContentWorkItemQueueBlockerSchema).default([])
});

export const ContentWorkItemQueueResponseSchema = z.object({
  queue_status: z.string(),
  candidate_count: z.number(),
  actionable_candidate_count: z.number(),
  minimum_actionable_candidate_count: z.number(),
  operator_summary: z.string(),
  candidates: z.array(ContentWorkItemQueueCandidateSchema).default([]),
  blockers: z.array(ContentWorkItemQueueBlockerSchema).default([]),
  ...ContentEvidenceTraceFields
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

export const ContentInventoryDuplicateRiskSchema = z.enum([
  "unknown",
  "clear",
  "review_required",
  "high"
]);

export const ContentClaimReferenceSchema = z.object({
  claim_id: z.string().optional(),
  id: z.string().optional(),
  claim_text: z.string().optional(),
  claim_type: z.string().optional(),
  status: z.string().optional(),
  evidence_ids: z.array(z.string()).optional(),
  source_connectors: z.array(z.string()).optional(),
  reviewer_id: z.string().nullable().optional(),
  reason: z.string().optional()
});

export const ContentSalesBriefSourceFactSchema = z.object({
  evidence_id: z.string(),
  source_connector: z.string(),
  summary: z.string()
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
  recommended_mode: z.string(),
  safe_next_step: z.string(),
  source_fact_ids: z.array(z.string()).default([])
});

export const ContentSalesBriefKnowledgeConstraintSchema = z.object({
  card_id: z.string(),
  constraint_type: z.string(),
  label: z.string(),
  reason: z.string()
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
    "measurement_sensitive_claim"
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
  source_connectors: z.array(z.string()).default([]),
  lifecycle_status: ContentKnowledgeLifecycleStatusSchema.nullable().optional(),
  confidence: z.number(),
  freshness: z.string(),
  usage_notes: z.array(z.string()).default([])
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

export const ContentServiceProfilePrivateSourceProposalSectionSchema = z.object({
  proposal_id: z.string(),
  source_id: z.string(),
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
  target_card_id: z.string(),
  target_card_title: z.string(),
  source_class_label: z.string(),
  source_locator_label: z.string(),
  review_status: ContentServiceProfilePrivateSourceProposalReviewStatusSchema,
  support_level: ContentServiceProfilePrivateSourceProposalSupportLevelSchema,
  risk_tier: ContentServiceProfilePrivateSourceProposalRiskTierSchema,
  confidence_label: z.string(),
  owner_role: z.string(),
  redacted: z.boolean(),
  blocked_claims: z.array(z.string()).default([]),
  safe_next_step: z.string(),
  promotion_allowed: z.boolean(),
  blocked_write_claim: z.string()
});

export const ContentServiceProfileCoverageGapSchema = z.object({
  gap_id: z.string(),
  area: z.string(),
  severity: z.enum(["blocker", "review_required", "thin", "stale"]),
  label: z.string(),
  reason: z.string(),
  needed_source_type: z.string(),
  safe_next_step: z.string(),
  example_work_item_ids: z.array(z.string()).default([])
});

export const ContentServiceProfileReviewActionSchema = z.object({
  action_id: z.string(),
  mode: z.enum(["prepare", "review_request"]),
  label: z.string(),
  reason: z.string(),
  blocked_write_claim: z.string(),
  required_human_role: z.string(),
  target_card_id: z.string().nullable().optional(),
  gap_id: z.string().nullable().optional()
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
  private_source_proposals: z.array(ContentServiceProfilePrivateSourceProposalSectionSchema).default([]),
  coverage_gaps: z.array(ContentServiceProfileCoverageGapSchema).default([]),
  review_actions: z.array(ContentServiceProfileReviewActionSchema).default([]),
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

export const ContentWorkItemPreflightRequestSchema = z.object({
  item: ContentWorkItemSchema,
  inventory_records: z.array(ContentInventoryRecordSchema).default([]),
  duplicate_risk: ContentInventoryDuplicateRiskSchema.default("unknown")
});

const ContentWorkItemBriefRequestFields = {
  item: ContentWorkItemSchema,
  inventory_records: z.array(ContentInventoryRecordSchema).default([]),
  duplicate_risk: ContentInventoryDuplicateRiskSchema.default("unknown"),
  claim_ledger: z.unknown(),
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

export const StructuredDraftSourceFactSchema = z.object({
  evidence_id: z.string(),
  source_connector: z.string(),
  summary: z.string()
});

export const StructuredDraftClaimMarkerSchema = z.object({
  claim_id: z.string(),
  claim_text: z.string(),
  claim_type: z.enum([
    "service_claim",
    "legal_requirement_claim",
    "risk_claim",
    "guarantee_claim",
    "performance_claim",
    "seo_claim",
    "business_outcome_claim",
    "environmental_claim"
  ]),
  status: z.enum([
    "allowed_with_evidence",
    "allowed_general",
    "needs_human_review",
    "blocked",
    "blocked_until_measurement"
  ]),
  strength: z.enum(["strong", "weak"]).default("strong"),
  required: z.boolean().default(false),
  evidence_ids: z.array(z.string()).default([]),
  source_connectors: z.array(z.string()).default([]),
  reviewer_id: z.string().nullable().optional()
});

export const StructuredDraftKnowledgeConstraintSchema = z.object({
  card_id: z.string(),
  constraint_type: z.string(),
  label: z.string(),
  reason: z.string()
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
  knowledge_constraints: z.array(StructuredDraftKnowledgeConstraintSchema).default([]),
  claim_markers: z.array(StructuredDraftClaimMarkerSchema).default([]),
  removed_or_blocked_claim_markers: z
    .array(StructuredDraftClaimMarkerSchema)
    .default([]),
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

export const StructuredDraftPreviewSchema = StructuredDraftOutputSchema.omit({
  draft_kind: true,
  language: true,
  claims_needing_review: true
});

export const StructuredDraftPreviewBlockerCodeSchema = z.enum([
  "missing_output",
  "missing_contract",
  "claims_need_review",
  "missing_source_facts",
  "section_missing_evidence",
  "unknown_evidence_reference",
  "unknown_claim_reference",
  "claim_missing_required_evidence",
  "missing_forbidden_claim_acknowledgement"
]);

export const StructuredDraftPreviewBlockerSchema = ContentBlockerBaseSchema.extend({
  code: StructuredDraftPreviewBlockerCodeSchema
});

export const StructuredDraftPreviewResultSchema = z.object({
  preview: StructuredDraftPreviewSchema.nullable().optional(),
  blockers: z.array(StructuredDraftPreviewBlockerSchema).default([])
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

export const ContentWorkItemStructuredDraftPreviewRequestSchema = z.object({
  contract: StructuredDraftGenerationContractSchema.nullable().optional(),
  output: StructuredDraftOutputSchema.nullable().optional()
});

export const ContentWorkItemStructuredDraftPreviewResponseSchema = z.object({
  preview_result: StructuredDraftPreviewResultSchema
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
  "missing_forbidden_claim_acknowledgement",
  "duplicate_risk_not_clear",
  "missing_measurement_window",
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
  claim_ledger: z.unknown().nullable().optional(),
  sales_brief: ContentSalesBriefSchema.nullable().optional(),
  duplicate_risk: z.string().default("clear")
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

export const ContentWorkItemRevisionPlanRequestSchema = z.object({
  item: ContentWorkItemSchema,
  quality_review: ContentQualityReviewSchema.nullable().optional()
});

export const ContentWorkItemRevisionPlanResponseSchema = z.object({
  item: ContentWorkItemSchema,
  revision_plan: ContentRevisionPlanSchema
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

export const ContentWorkItemHumanReviewRequestSchema = z.object({
  item: ContentWorkItemSchema,
  review: ContentHumanReviewSchema.nullable().optional(),
  draft_package: ContentDraftPackageSchema.nullable().optional(),
  claim_ledger: z.unknown().nullable().optional()
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

export const ContentWordPressDraftExecutionResultSchema = z.object({
  status: z.enum(["dry_run_ready", "created", "blocked"]),
  mode: z.enum(["dry_run", "live"]),
  boundary: ContentWordPressDraftExecutionBoundarySchema,
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
  content_url: z.string().nullable().optional()
});

export const ContentMeasurementOutcomeInterpretationSchema = z.object({
  id: z.string(),
  work_item_id: z.string(),
  measurement_window_id: z.string(),
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
  item: ContentWorkItemSchema,
  handoff: ContentWordPressDraftHandoffSchema.nullable().optional(),
  baseline_period: ContentDateRangeSchema,
  observation_period: ContentDateRangeSchema,
  allowed_metrics: z.array(z.string()).default([]),
  source_connectors: z.array(z.string()).default([])
});

export const ContentWorkItemMeasurementOutcomeRequestSchema = z.object({
  window: ContentMeasurementWindowSchema,
  observed_metrics: z.array(ContentMeasurementObservedMetricSchema).default([]),
  as_of: z.string()
});

export const ContentWorkItemMeasurementOutcomeResponseSchema = z.object({
  outcome: ContentMeasurementOutcomeInterpretationSchema
});

export const ContentWorkflowOperatorStepSchema = z.object({
  id: z.string(),
  title: z.string(),
  status_label: z.string(),
  summary: z.string()
});

export const ContentWorkItemWorkflowSnapshotResponseSchema = z.object({
  response_type: z.literal("workflow_snapshot").default("workflow_snapshot"),
  preflight: ContentWorkItemPreflightResponseSchema,
  sales_brief: ContentWorkItemSalesBriefResponseSchema,
  draft_package: ContentWorkItemDraftPackageResponseSchema,
  structured_generation: ContentWorkItemStructuredDraftGenerationResponseSchema,
  human_review: ContentWorkItemHumanReviewResponseSchema,
  wordpress_handoff: ContentWorkItemWordPressDraftHandoffResponseSchema,
  measurement_window: ContentWorkItemMeasurementWindowResponseSchema,
  operator_steps: z.array(ContentWorkflowOperatorStepSchema).default([])
});

export const ContentWorkItemBlockedSnapshotResponseSchema = z.object({
  response_type: z.literal("blocked_snapshot"),
  work_item_id: z.string(),
  decision_id: z.string(),
  title: z.string(),
  topic: z.string(),
  status_label: z.string(),
  reason: z.string(),
  safe_next_step: z.string(),
  recommended_mode: z.string(),
  preflight_status: z.string(),
  blockers: z.array(ContentWorkItemQueueBlockerSchema).default([]),
  ...ContentEvidenceTraceFields,
  candidate: ContentWorkItemQueueCandidateSchema
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
  recommended_mode: z.string(),
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

export type ContentWorkItem = z.infer<typeof ContentWorkItemSchema>;
export type ContentWorkItemQueueCandidate = z.infer<
  typeof ContentWorkItemQueueCandidateSchema
>;
export type ContentWorkItemQueueResponse = z.infer<typeof ContentWorkItemQueueResponseSchema>;
export type ContentWorkItemPreflightResponse = z.infer<
  typeof ContentWorkItemPreflightResponseSchema
>;
export type ContentWorkItemPreflightRequest = z.input<
  typeof ContentWorkItemPreflightRequestSchema
>;
export type ContentWorkItemSalesBriefResponse = z.infer<
  typeof ContentWorkItemSalesBriefResponseSchema
>;
export type ContentWorkItemSalesBriefRequest = z.input<
  typeof ContentWorkItemSalesBriefRequestSchema
>;
export type ContentKnowledgeCard = z.infer<typeof ContentKnowledgeCardSchema>;
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
export type ContentWorkItemStructuredDraftGenerationRequest = z.input<
  typeof ContentWorkItemStructuredDraftGenerationRequestSchema
>;
export type ContentWorkItemStructuredDraftGenerationResponse = z.infer<
  typeof ContentWorkItemStructuredDraftGenerationResponseSchema
>;
export type ContentWorkItemStructuredDraftRuntimeRequest = z.input<
  typeof ContentWorkItemStructuredDraftRuntimeRequestSchema
>;
export type ContentWorkItemStructuredDraftRuntimeResponse = z.infer<
  typeof ContentWorkItemStructuredDraftRuntimeResponseSchema
>;
export type ContentWorkItemStructuredDraftPreviewRequest = z.input<
  typeof ContentWorkItemStructuredDraftPreviewRequestSchema
>;
export type ContentWorkItemStructuredDraftPreviewResponse = z.infer<
  typeof ContentWorkItemStructuredDraftPreviewResponseSchema
>;
export type ContentQualityReview = z.infer<typeof ContentQualityReviewSchema>;
export type ContentRevisionPlan = z.infer<typeof ContentRevisionPlanSchema>;
export type ContentWorkItemQualityReviewRequest = z.input<
  typeof ContentWorkItemQualityReviewRequestSchema
>;
export type ContentWorkItemQualityReviewResponse = z.infer<
  typeof ContentWorkItemQualityReviewResponseSchema
>;
export type ContentWorkItemRevisionPlanRequest = z.input<
  typeof ContentWorkItemRevisionPlanRequestSchema
>;
export type ContentWorkItemRevisionPlanResponse = z.infer<
  typeof ContentWorkItemRevisionPlanResponseSchema
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
export type ContentWorkItemMeasurementWindowResponse = z.infer<
  typeof ContentWorkItemMeasurementWindowResponseSchema
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
export type ContentWorkflowOperatorStep = z.infer<typeof ContentWorkflowOperatorStepSchema>;
export type ContentWorkItemWorkflowSnapshotResponse = z.infer<
  typeof ContentWorkItemWorkflowSnapshotResponseSchema
>;
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
