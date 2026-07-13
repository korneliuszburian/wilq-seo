import { z } from "zod";

import { ActionPreviewCardViewModelSchema } from "./actions";
import { MetricFactSchema } from "./connectors";
import { AdsSearchTermMetricRowSchema } from "./ads_search_terms";
import { AdsKeywordPlannerIdeaRowSchema } from "./ads_keyword_planner_contracts";

export const AdsCustomSegmentTargetingPreviewSchema = z.object({
  id: z.string(),
  custom_segment_preview_id: z.string(),
  target_scope: z.literal("campaign_context_review"),
  campaign_id: z.string().nullable().optional(),
  campaign_name: z.string().nullable().optional(),
  operation_type: z.literal("custom_segment_targeting_review"),
  reason: z.string(),
  required_validation: z.array(z.string()),
  required_validation_labels: z.array(z.string()).optional().default([]),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([]),
  api_mutation_ready: z.boolean(),
  apply_allowed: z.boolean(),
  destructive: z.boolean()
});

export const AdsCustomSegmentApplySafetyReviewSchema = z.object({
  id: z.string(),
  custom_segment_preview_id: z.string(),
  safety_contract: z.literal("custom_segment_apply_safety_v1"),
  status: z.literal("blocked"),
  status_label: z.string().optional().default("zablokowane"),
  reason: z.string(),
  missing_requirements: z.array(z.string()),
  missing_requirement_labels: z.array(z.string()).optional().default([]),
  required_validation: z.array(z.string()),
  required_validation_labels: z.array(z.string()).optional().default([]),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([]),
  evidence_ids: z.array(z.string()),
  audit_required: z.boolean(),
  api_mutation_ready: z.boolean(),
  apply_allowed: z.boolean(),
  destructive: z.boolean()
});

export const AdsCustomSegmentPayloadPreviewSchema = z.object({
  id: z.string(),
  custom_segment_name: z.string(),
  member_type: z.literal("KEYWORD"),
  member_type_label: z.string().optional().default("słowa kluczowe"),
  source_terms: z.array(z.string()),
  campaign_id: z.string().nullable().optional(),
  campaign_name: z.string().nullable().optional(),
  reason: z.string(),
  evidence_ids: z.array(z.string()),
  source_metric_names: z.array(z.string()),
  required_validation: z.array(z.string()),
  required_validation_labels: z.array(z.string()).optional().default([]),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([]),
  targeting_preview: z.array(AdsCustomSegmentTargetingPreviewSchema).optional().default([]),
  safety_review: AdsCustomSegmentApplySafetyReviewSchema,
  api_mutation_ready: z.boolean(),
  apply_allowed: z.boolean(),
  destructive: z.boolean()
});

export const AdsCustomSegmentAudienceForecastRowSchema = z.object({
  id: z.string(),
  candidate_id: z.string(),
  custom_segment_name: z.string(),
  status: z.enum(["ready", "missing_forecast"]),
  forecast_available: z.boolean(),
  audience_size: z.number().int().nonnegative().nullable().optional(),
  source_terms: z.array(z.string()),
  reason: z.string(),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([])
});

export const AdsCustomSegmentAudienceForecastReadContractSchema = z.object({
  id: z.string(),
  status: z.enum(["ready", "blocked"]),
  status_label: z.string().default(""),
  title: z.string(),
  summary: z.string(),
  checked_candidate_count: z.number().int().nonnegative(),
  forecast_row_count: z.number().int().nonnegative(),
  forecast_rows: z.array(AdsCustomSegmentAudienceForecastRowSchema),
  missing_read_contracts: z.array(z.string()),
  missing_read_contract_labels: z.array(z.string()).optional().default([]),
  operator_review_gates: z.array(z.string()).optional().default([]),
  operator_review_gate_labels: z.array(z.string()).optional().default([]),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([]),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  next_step: z.string()
});

export const AdsCustomSegmentCandidateSchema = z.object({
  id: z.string(),
  name: z.string(),
  intent: z.string(),
  review_priority: z
    .enum(["pilne", "wysokie", "normalne", "niski sygnał"])
    .default("normalne"),
  review_score: z.number().min(0).max(100).default(0),
  review_reason: z.string(),
  human_review_gates: z.array(z.string()).default([]),
  human_review_gate_labels: z.array(z.string()).optional().default([]),
  source_terms: z.array(z.string()),
  rejected_terms: z.array(z.string()),
  rejection_reasons: z.array(z.string()),
  source_quality: z
    .object({
      total_terms: z.number().int().nonnegative().default(0),
      accepted_terms: z.number().int().nonnegative().default(0),
      rejected_terms: z.number().int().nonnegative().default(0),
      missing_metric_terms: z.number().int().nonnegative().default(0),
      rejection_reasons: z.record(z.string(), z.number().int().nonnegative()).default({}),
      rejection_reason_labels: z.record(z.string(), z.number().int().nonnegative()).default({})
    })
    .default({
      total_terms: 0,
      accepted_terms: 0,
      rejected_terms: 0,
      missing_metric_terms: 0,
      rejection_reasons: {},
      rejection_reason_labels: {}
    }),
  search_term_rows: z.array(AdsSearchTermMetricRowSchema),
  keyword_planner_ideas: z.array(AdsKeywordPlannerIdeaRowSchema).optional().default([]),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  metric_facts: z.array(MetricFactSchema),
  confidence: z.enum(["low", "medium", "high"]),
  confidence_label: z.string().optional().default("niska"),
  validation_status: z.enum(["pending_validation", "blocked"]),
  validation_status_label: z.string().optional().default("do sprawdzenia"),
  payload_preview: AdsCustomSegmentPayloadPreviewSchema.nullable().optional(),
  preview_card: ActionPreviewCardViewModelSchema.nullable().optional(),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([]),
  next_step: z.string()
});

export const AdsCustomSegmentsReadContractSchema = z.object({
  id: z.string(),
  status: z.enum(["ready", "blocked"]),
  status_label: z.string().default(""),
  title: z.string(),
  summary: z.string(),
  candidates: z.array(AdsCustomSegmentCandidateSchema),
  payload_preview: z.array(AdsCustomSegmentPayloadPreviewSchema),
  audience_forecast_read_contract:
    AdsCustomSegmentAudienceForecastReadContractSchema,
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  missing_read_contracts: z.array(z.string()),
  missing_read_contract_labels: z.array(z.string()).optional().default([]),
  missing_read_contract_summary_label: z.string().default(""),
  operator_review_gates: z.array(z.string()).optional().default([]),
  operator_review_gate_labels: z.array(z.string()).optional().default([]),
  operator_review_gate_summary_label: z.string().default(""),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([]),
  action_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  action_summary_label: z.string().default(""),
  next_step: z.string()
});


