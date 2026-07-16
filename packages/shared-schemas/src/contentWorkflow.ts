import { z } from "zod";

import { ContentDraftRevisionBindingSchema } from "./actions";

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
  wordpress_content_word_count: z.number().int().nonnegative().nullable().optional(),
  wordpress_content_inventory_status: z.enum(["available", "missing"]).default("missing"),
  wordpress_content_inventory_note: z.string().nullable().optional(),
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
  query_terms: z.array(z.string().refine((value) => value.trim().length > 0)).default([]),
  evidence_ids: z.array(z.string().refine((value) => value.trim().length > 0)).default([]),
  claim_ids: z.array(z.string().refine((value) => value.trim().length > 0)).default([])
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
  meta_title: z.string().nullable().optional(),
  meta_description: z.string().nullable().optional(),
  meta_write_status: z.enum(["not_present", "review_required", "mapped"])
    .default("not_present"),
  metadata_blockers: z.array(z.object({
    code: z.literal("missing_wordpress_meta_mapping"),
    label: z.string(),
    reason: z.string(),
    next_step: z.string()
  })).default([]),
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
  wordpress_post_id: z.string().nullable().optional(),
  external_write_attempted: z.boolean(),
  blockers: z.array(ContentWordPressDraftExecutionBlockerSchema).default([])
});

export const ContentWordPressDraftReadbackBlockerSchema = z.object({
  code: z.enum(["missing_wordpress_post_id", "wordpress_draft_read_failed"]),
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
  modified_gmt: z.string(),
  content_summary: z.string(),
  content_word_count: z.number().nullable().optional(),
  acf_field_count: z.number().nullable().optional(),
  acf_field_names: z.array(z.string()).default([]),
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
  mode: z.enum(["dry_run", "live"]).default("dry_run"),
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
  claim_ids: z.array(z.string()).default([])
});

export const ContentDraftRevisionProposalMetadataSchema = z
  .object({
    source: z.literal("codex_app_server"),
    codex_run_id: z.string().refine((value) => value.trim().length > 0),
    selected_section_headings: z
      .array(z.string().refine((value) => value.trim().length > 0))
      .min(1),
    section_lineage: z.array(ContentDraftRevisionProposalSectionLineageSchema).min(1),
    quality_verdict: z.enum(["needs_changes", "reviewable", "ready_for_human_review"]),
    quality_finding_codes: z.array(z.string()).default([]),
    review_scope: z.enum([
      "persisted_selected_sections_and_declared_lineage",
      "persisted_full_document_and_declared_lineage"
    ]),
    semantic_review_required: z.literal(true)
  })
  .superRefine((metadata, context) => {
    const headings = metadata.selected_section_headings;
    const lineageHeadings = metadata.section_lineage.map((lineage) => lineage.heading);
    if (
      new Set(headings).size !== headings.length ||
      headings.length !== lineageHeadings.length ||
      headings.some((heading, index) => heading !== lineageHeadings[index])
    ) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["section_lineage"],
        message: "proposal lineage must match unique selected headings in order"
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

export const ContentDraftRevisionInternalLinkSchema = z.object({
  link_id: z.string().min(1),
  placement: z.string().min(1),
  target_url: z.string().url().refine((value) => {
    const hostname = new URL(value).hostname.toLowerCase();
    return hostname === "ekologus.pl" || hostname === "www.ekologus.pl";
  }, "Internal links must target the public Ekologus site."),
  anchor_text: z.string().min(1),
  evidence_ids: z.array(z.string().refine((value) => value.trim().length > 0)).min(1),
  claim_ids: z.array(z.string().refine((value) => value.trim().length > 0)).default([])
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
  final_canonical_url: z.string(),
  title: z.string().refine((value) => value.trim().length > 0),
  page_assets: ContentDraftRevisionPageAssetsSchema.nullable().optional(),
  sections: z.array(ContentDraftRevisionSectionSchema).min(1),
  faq: z.array(ContentDraftRevisionFaqItemSchema).default([]),
  cta_blocks: z.array(ContentDraftRevisionCtaBlockSchema).default([]),
  internal_links: z.array(ContentDraftRevisionInternalLinkSchema).default([]),
  proposal_metadata: ContentDraftRevisionProposalMetadataSchema.nullable().optional(),
  publish_ready: z.literal(false),
  created_by: z.string().refine((value) => value.trim().length > 0),
  created_at: z.string()
}).superRefine((revision, context) => {
  if (revision.schema_version !== "wilq_content_draft_revision_v2") return;
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
  created_by: z.string().refine((value) => value.trim().length > 0)
});

export const ContentDraftRevisionSaveResponseSchema = z.object({
  status: z.enum(["created", "idempotent"]),
  revision: ContentDraftRevisionSchema,
  workspace: ContentDraftRevisionWorkspaceSchema
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
    "digest_mismatch"
  ]),
  current_revision_id: z.string().nullable(),
  current_digest: z.string().regex(/^[0-9a-f]{64}$/).nullable(),
  safe_next_step: z.string()
});

export const ContentCodexSectionProposalRequestSchema = z
  .object({
    expected_base_digest: z.string().regex(/^[0-9a-f]{64}$/),
    selected_section_headings: z
      .array(z.string().refine((value) => value.trim().length > 0))
      .min(1),
    requested_by: z.string().refine((value) => value.trim().length > 0)
  })
  .strict()
  .superRefine((request, context) => {
    if (new Set(request.selected_section_headings).size !== request.selected_section_headings.length) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["selected_section_headings"],
        message: "selected section headings must be unique"
      });
    }
  });

export const ContentCodexSectionProposalBlockerCodeSchema = z.enum([
  "missing_planning_binding",
  "missing_base_revision",
  "stale_base_revision",
  "revision_not_ready_for_proposal",
  "stale_content_context",
  "missing_generation_contract",
  "unknown_selected_section",
  "ambiguous_claim_marker",
  "runtime_blocked",
  "runtime_failed",
  "invalid_structured_output",
  "section_scope_mismatch",
  "proposal_contract_blocked",
  "quality_blocked",
  "revision_conflict"
]);

export const ContentCodexSectionProposalBlockerSchema = z.object({
  code: ContentCodexSectionProposalBlockerCodeSchema,
  label: z.string(),
  reason: z.string(),
  next_step: z.string(),
  source_codes: z.array(z.string()).default([])
});

export const ContentCodexRuntimeTraceSchema = z.object({
  status: z.enum(["not_started", "completed", "blocked", "failed"]),
  thread_id: z.string().nullable(),
  turn_id: z.string().nullable(),
  event_methods: z.array(z.string()).default([]),
  item_types: z.array(z.string()).default([]),
  external_call_attempted: z.boolean()
});

export const ContentCodexSectionProposalResponseSchema = z
  .object({
    status: z.enum(["created", "idempotent", "blocked", "failed", "conflict"]),
    run_id: z.string().nullable(),
    work_item_id: z.string(),
    base_revision_id: z.string(),
    selected_section_headings: z.array(z.string()),
    revision: ContentDraftRevisionSchema.nullable(),
    quality_review: ContentQualityReviewSchema.nullable(),
    quality_review_scope: z.literal("persisted_selected_sections_and_declared_lineage"),
    semantic_review_required: z.literal(true),
    runtime: ContentCodexRuntimeTraceSchema,
    evidence_ids: z.array(z.string()).default([]),
    source_connectors: z.array(z.string()).default([]),
    blockers: z.array(ContentCodexSectionProposalBlockerSchema).default([]),
    safe_next_step: z.string(),
    publish_ready: z.literal(false)
  })
  .superRefine((response, context) => {
    const created = response.status === "created" || response.status === "idempotent";
    if (
      created &&
      (response.run_id === null ||
        response.revision === null ||
        response.quality_review === null ||
        response.quality_review.verdict === "blocked" ||
        response.runtime.status !== "completed" ||
        response.runtime.external_call_attempted ||
        response.blockers.length > 0)
    ) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["status"],
        message: "created proposal requires an unblocked reviewable revision"
      });
    }
    const metadata = response.revision?.proposal_metadata;
    if (
      created &&
      (!metadata ||
        metadata.codex_run_id !== response.run_id ||
        response.revision?.base_revision_id !== response.base_revision_id ||
        JSON.stringify(metadata.selected_section_headings) !==
          JSON.stringify(response.selected_section_headings))
    ) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["revision", "proposal_metadata"],
        message: "created proposal revision must match the exact run, base and selected sections"
      });
    }
    if (!created && (response.revision !== null || response.blockers.length === 0)) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["status"],
        message: "non-created proposal requires blockers and no revision"
      });
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
  evidence_ids: z.array(z.string()).default([]),
  knowledge_card_ids: z.array(z.string()).default([]),
  review_action_id: z.string().nullable().optional(),
  review_action_label: z.string().nullable().optional()
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
  evidence_ids: [],
  knowledge_card_ids: []
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
  service_card_id: z.string().nullable(),
  section_headings: z.array(z.string()),
  section_mapping_status: z.enum(["lexical_relevance", "page_only"]),
  period: z.string().min(1),
  freshness: z.enum(["fresh", "stale", "missing", "blocked"]),
  collected_at: z.string().nullable(),
  evidence_ids: z.array(z.string()).min(1),
  impressions: z.number().int().nullable(),
  clicks: z.number().int().nullable(),
  ctr: z.number().nullable(),
  average_position: z.number().nullable(),
  average_monthly_searches: z.number().int().nullable()
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

export const ContentPlanningProposalSchema = z.object({
  work_item_id: z.string().min(1),
  planning_digest: z.string().regex(/^[0-9a-f]{64}$/),
  proposal_id: z.string().nullable().optional(),
  proposal_version: z.number().int().positive().nullable().optional(),
  codex_run_id: z.string().nullable().optional(),
  generation_status: z.enum(["baseline", "codex_generated"]).default("baseline"),
  input_schema_version: z.string().default("wilq_content_planning_input_v1"),
  criteria_version: z.string().default("wilq_people_first_planning_v1"),
  planning_input_digest: z.string().regex(/^[0-9a-f]{64}$/).nullable().optional(),
  final_canonical_url: z.string().min(1),
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
  internal_link_directions: z.array(z.string()),
  sections: z.array(z.object({
    section_id: z.string().default(""),
    heading: z.string().min(1),
    purpose: z.string().min(1),
    reader_question: z.string().default(""),
    inventory_disposition: ContentPlanningInventoryDispositionSchema.default("create"),
    inventory_heading: z.string().nullable().optional(),
    query_terms: z.array(z.string()).default([]),
    evidence_ids: z.array(z.string()),
    claim_ids: z.array(z.string()).default([])
  })).min(1),
  search_demand: z.object({
    status: z.enum(["available", "missing"]),
    gsc_query_rows: z.array(ContentSearchDemandRowSchema),
    ads_term_rows: z.array(ContentSearchDemandRowSchema),
    keyword_planner_rows: z.array(ContentSearchDemandRowSchema),
    source_connectors: z.array(z.string()),
    evidence_ids: z.array(z.string()),
    optional_ads_status: z.enum(["exact_rows_available", "not_exactly_mapped"]),
    safe_next_step: z.string().min(1)
  }),
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
  evidence_ids: z.array(z.string()),
  source_connectors: z.array(z.string()),
  created_at: z.string().nullable().optional()
});

export const ContentPlanningWorkspaceSchema = z.object({
  proposal: ContentPlanningProposalSchema,
  scope_decision: ContentPlanningDecisionSchema.nullable(),
  section_map_decision: ContentPlanningDecisionSchema.nullable(),
  scope_current: z.boolean(),
  section_map_current: z.boolean()
});

export const ContentPlanningReviewRequestSchema = z.object({
  stage: z.enum(["scope", "section_map"]),
  expected_planning_digest: z.string().regex(/^[0-9a-f]{64}$/),
  service_card_id: z.string().nullable().optional(),
  decision: z.enum(["approved", "needs_changes"]),
  reviewed_by: z.string().min(1),
  checked_items: z.array(z.string()),
  notes: z.string()
});

export const ContentPlanningReviewResponseSchema = z.object({
  status: z.enum(["recorded", "idempotent"]),
  decision: ContentPlanningDecisionSchema,
  planning_workspace: ContentPlanningWorkspaceSchema
});

export const ContentPlanningReviewConflictSchema = z.object({
  detail: z.string().min(1)
});

export const ContentPlanningProposalRequestSchema = z.object({
  service_card_id: z.string().min(1),
  expected_planning_input_digest: z.string().regex(/^[0-9a-f]{64}$/),
  operator_hint: z.string().max(500).default(""),
  requested_by: z.string().min(1)
});

export const ContentPlanningProposalBlockerSchema = z.object({
  code: z.string().min(1),
  label: z.string().min(1),
  reason: z.string().min(1),
  next_step: z.string().min(1),
  source_codes: z.array(z.string()).default([])
});

export const ContentPlanningProposalResponseSchema = z.object({
  status: z.enum([
    "not_generated",
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
  proposal: ContentPlanningProposalSchema.nullable().optional(),
  runtime: ContentCodexRuntimeTraceSchema,
  blockers: z.array(ContentPlanningProposalBlockerSchema).default([]),
  safe_next_step: z.string().min(1),
  publish_ready: z.literal(false)
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
  status: z.enum(["created", "blocked", "failed", "conflict"]),
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
  } else if (response.revision || response.blockers.length === 0) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      message: "non-created initial draft requires blockers without revision"
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
export type ContentClaimLedger = z.infer<typeof ContentClaimLedgerSchema>;
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
export type ContentDraftRevisionReviewRequest = z.input<
  typeof ContentDraftRevisionReviewRequestSchema
>;
export type ContentDraftRevisionReviewResponse = z.infer<
  typeof ContentDraftRevisionReviewResponseSchema
>;
export type ContentDraftRevisionConflict = z.infer<
  typeof ContentDraftRevisionConflictSchema
>;
export type ContentCodexSectionProposalRequest = z.input<
  typeof ContentCodexSectionProposalRequestSchema
>;
export type ContentCodexSectionProposalResponse = z.infer<
  typeof ContentCodexSectionProposalResponseSchema
>;
export type ContentWorkflowOperatorStep = z.infer<typeof ContentWorkflowOperatorStepSchema>;
export type ContentPlanningWorkspace = z.infer<typeof ContentPlanningWorkspaceSchema>;
export type ContentPlanningProposal = z.infer<typeof ContentPlanningProposalSchema>;
export type ContentPlanningProposalRequest = z.input<
  typeof ContentPlanningProposalRequestSchema
>;
export type ContentPlanningProposalResponse = z.infer<
  typeof ContentPlanningProposalResponseSchema
>;
export type ContentInitialDraftRequest = z.input<typeof ContentInitialDraftRequestSchema>;
export type ContentInitialDraftResponse = z.infer<typeof ContentInitialDraftResponseSchema>;
export type ContentPlanningReviewRequest = z.input<typeof ContentPlanningReviewRequestSchema>;
export type ContentPlanningReviewResponse = z.infer<typeof ContentPlanningReviewResponseSchema>;
export type ContentPlanningReviewConflict = z.infer<typeof ContentPlanningReviewConflictSchema>;
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
