import { z } from "zod";

import { ActionPreviewCardViewModelSchema } from "./actions";
import { MetricFactSchema } from "./connectors";

export const AdsRecommendationApplyPreviewSchema = z.object({
  id: z.string(),
  recommendation_id: z.string().nullable().optional(),
  recommendation_resource_name: z.string().nullable().optional(),
  recommendation_type: z.string(),
  recommendation_type_label: z.string().optional().default(""),
  campaign_id: z.string().nullable().optional(),
  campaign_budget_id: z.string().nullable().optional(),
  operation_type: z.literal("ApplyRecommendationOperation"),
  operation_type_label: z.string().optional().default(""),
  reason: z.string(),
  evidence_ids: z.array(z.string()),
  source_metric_names: z.array(z.string()),
  required_validation: z.array(z.string()),
  required_validation_labels: z.array(z.string()).optional().default([]),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([]),
  api_mutation_ready: z.boolean(),
  apply_allowed: z.boolean(),
  destructive: z.boolean()
});

export const AdsRecommendationRowSchema = z.object({
  recommendation_id: z.string().nullable().optional(),
  recommendation_resource_name: z.string().nullable().optional(),
  recommendation_type: z.string(),
  recommendation_type_label: z.string().optional().default(""),
  review_priority: z
    .enum(["pilne", "wysokie", "normalne", "niski sygnał"])
    .default("normalne"),
  review_score: z.number().min(0).max(100).default(0),
  review_reason: z.string(),
  human_review_gates: z.array(z.string()).default([]),
  human_review_gate_labels: z.array(z.string()).optional().default([]),
  human_review_gate_summary_label: z.string().optional().default(""),
  dismissed: z.boolean(),
  campaign_id: z.string().nullable().optional(),
  campaign_budget_id: z.string().nullable().optional(),
  campaign_count: z.number().nullable().optional(),
  impact_available: z.boolean(),
  base_clicks: z.number().nullable().optional(),
  potential_clicks: z.number().nullable().optional(),
  delta_clicks: z.number().nullable().optional(),
  base_impressions: z.number().nullable().optional(),
  potential_impressions: z.number().nullable().optional(),
  delta_impressions: z.number().nullable().optional(),
  base_cost_micros: z.number().nullable().optional(),
  potential_cost_micros: z.number().nullable().optional(),
  delta_cost_micros: z.number().nullable().optional(),
  base_conversions: z.number().nullable().optional(),
  potential_conversions: z.number().nullable().optional(),
  delta_conversions: z.number().nullable().optional(),
  base_conversion_value: z.number().nullable().optional(),
  potential_conversion_value: z.number().nullable().optional(),
  delta_conversion_value: z.number().nullable().optional(),
  evidence_ids: z.array(z.string()),
  metric_facts: z.array(MetricFactSchema),
  payload_preview: AdsRecommendationApplyPreviewSchema.nullable().optional(),
  preview_card: ActionPreviewCardViewModelSchema.nullable().optional(),
  missing_metrics: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([]),
  blocked_claim_summary_label: z.string().optional().default("")
});

export const AdsRecommendationsReadContractSchema = z.object({
  id: z.string(),
  status: z.enum(["ready", "blocked"]),
  title: z.string(),
  summary: z.string(),
  allowed_metrics: z.array(z.string()),
  missing_read_contracts: z.array(z.string()),
  missing_read_contract_summary_label: z.string().optional().default(""),
  operator_review_gates: z.array(z.string()).optional().default([]),
  operator_review_gate_labels: z.array(z.string()).optional().default([]),
  operator_review_gate_summary_label: z.string().optional().default(""),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([]),
  blocked_claim_summary_label: z.string().optional().default(""),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  recommendation_rows: z.array(AdsRecommendationRowSchema),
  payload_preview: z.array(AdsRecommendationApplyPreviewSchema),
  action_ids: z.array(z.string()),
  next_step: z.string()
});

export const AdsImpressionShareRowSchema = z.object({
  campaign_id: z.string().nullable().optional(),
  campaign_name: z.string(),
  campaign_status: z.string().nullable().optional(),
  campaign_status_label: z.string().optional().default(""),
  advertising_channel_type: z.string().nullable().optional(),
  advertising_channel_type_label: z.string().optional().default(""),
  search_impression_share: z.number().nullable().optional(),
  search_budget_lost_impression_share: z.number().nullable().optional(),
  search_rank_lost_impression_share: z.number().nullable().optional(),
  evidence_ids: z.array(z.string()),
  metric_facts: z.array(MetricFactSchema),
  missing_metrics: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([]),
  blocked_claim_summary_label: z.string().optional().default("")
});

export const AdsImpressionShareReadContractSchema = z.object({
  id: z.string(),
  status: z.enum(["ready", "blocked"]),
  title: z.string(),
  summary: z.string(),
  empty_state_message: z.string().optional().default(""),
  allowed_metrics: z.array(z.string()),
  missing_read_contracts: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  impression_share_rows: z.array(AdsImpressionShareRowSchema),
  next_step: z.string()
});
