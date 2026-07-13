import { z } from "zod";

import { ActionPreviewCardViewModelSchema } from "./actions";
import { MetricFactSchema } from "./connectors";

export const AdsDiagnosticSectionSchema = z.object({
  id: z.string(),
  title: z.string(),
  status: z.enum(["ready", "blocked", "missing"]),
  status_label: z.string().default(""),
  summary: z.string(),
  diagnosis: z.string(),
  next_step: z.string(),
  source_connectors: z.array(z.string()),
  source_connector_labels: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  metric_facts: z.array(MetricFactSchema),
  metric_fact_labels: z.record(z.string(), z.string()).default({}),
  action_ids: z.array(z.string()),
  action_summary_label: z.string().default(""),
  knowledge_card_ids: z.array(z.string()).optional().default([]),
  expert_rule_ids: z.array(z.string()).optional().default([]),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).default([]),
  risk: z.enum(["low", "medium", "high", "critical"])
});

export const AdsBlockedHandoffSchema = z.object({
  id: z.string(),
  status: z.enum(["ready", "blocked"]),
  status_label: z.string().optional().default(""),
  title: z.string(),
  summary: z.string(),
  marketer_message: z.string(),
  repair_steps: z.array(z.string()),
  allowed_demo_claims: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).default([]),
  source_connectors: z.array(z.string()),
  source_connector_labels: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  action_ids: z.array(z.string()),
  action_summary_label: z.string().default("")
});

export const AdsCampaignMetricRowSchema = z.object({
  campaign_id: z.string().nullable().optional(),
  campaign_name: z.string(),
  campaign_status: z.string().nullable().optional(),
  campaign_status_label: z.string().optional().default(""),
  advertising_channel_type: z.string().nullable().optional(),
  advertising_channel_type_label: z.string().optional().default(""),
  clicks: z.number().nullable().optional(),
  clicks_label: z.string().optional().default(""),
  impressions: z.number().nullable().optional(),
  impressions_label: z.string().optional().default(""),
  cost_micros: z.number().nullable().optional(),
  cost_label: z.string().optional().default(""),
  conversions: z.number().nullable().optional(),
  conversions_label: z.string().optional().default(""),
  conversion_value: z.number().nullable().optional(),
  conversion_value_label: z.string().optional().default(""),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  metric_facts: z.array(MetricFactSchema),
  missing_metrics: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([]),
  blocked_claim_summary_label: z.string().optional().default(""),
  target_status: z
    .enum([
      "within_target",
      "outside_target",
      "spend_without_conversions",
      "insufficient_data",
      "no_target"
    ])
    .default("no_target"),
  target_status_label: z.string().default("brak targetu"),
  review_priority: z
    .enum(["pilne", "wysokie", "normalne", "niski sygnał"])
    .default("niski sygnał"),
  review_score: z.number().min(0).max(100).default(0),
  review_reason: z.string().default(""),
  human_review_gates: z.array(z.string()).default([]),
  human_review_gate_labels: z.array(z.string()).optional().default([]),
  human_review_gate_summary_label: z.string().optional().default("")
});

export const AdsCampaignReadContractSchema = z.object({
  id: z.string(),
  status: z.enum(["ready", "blocked"]),
  status_label: z.string().optional().default(""),
  title: z.string(),
  summary: z.string(),
  allowed_metrics: z.array(z.string()),
  missing_read_contracts: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  campaign_rows: z.array(AdsCampaignMetricRowSchema),
  next_step: z.string()
});

export const AdsAccountCurrencyReadContractSchema = z.object({
  id: z.string(),
  status: z.enum(["ready", "blocked"]),
  title: z.string(),
  summary: z.string(),
  currency_code: z.string().nullable().optional(),
  allowed_metrics: z.array(z.string()),
  missing_read_contracts: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  next_step: z.string()
});

export const AdsBusinessTargetInterpretationSchema = z.object({
  id: z.string(),
  interpretation_contract: z.literal("ads_business_target_interpretation_v1"),
  status: z.enum(["ready", "preliminary", "blocked"]),
  status_label: z.string().optional().default(""),
  summary: z.string(),
  allowed_uses: z.array(z.string()),
  allowed_use_labels: z.array(z.string()).optional().default([]),
  blocked_uses: z.array(z.string()),
  blocked_use_labels: z.array(z.string()).optional().default([]),
  missing_requirements: z.array(z.string()),
  missing_requirement_labels: z.array(z.string()).optional().default([]),
  required_validation: z.array(z.string()),
  required_validation_labels: z.array(z.string()).optional().default([]),
  policy_ids: z.array(z.string()),
  policy_summary_label: z.string().optional().default(""),
  evidence_ids: z.array(z.string()),
  action_ids: z.array(z.string()).optional().default([]),
  action_summary_label: z.string().optional().default(""),
  apply_allowed: z.boolean(),
  destructive: z.boolean()
});

export const AdsStrategyReviewReadinessContractSchema = z.object({
  id: z.string(),
  status: z.enum(["ready", "blocked"]),
  status_label: z.string().optional().default(""),
  title: z.string(),
  summary: z.string(),
  latest_review_status: z
    .enum(["missing", "approved_for_prepare", "needs_changes", "rejected", "deferred"])
    .optional()
    .default("missing"),
  latest_review_status_label: z.string().optional().default(""),
  latest_review_outcome: z
    .enum(["approved_for_prepare", "needs_changes", "rejected", "deferred"])
    .nullable()
    .optional(),
  reviewed_by: z.string().nullable().optional(),
  reviewed_at: z.string().nullable().optional(),
  current_context: z.record(
    z.string(),
    z.union([z.string(), z.number(), z.boolean(), z.array(z.string()), z.null()])
  ),
  required_validation: z.array(z.string()),
  required_validation_labels: z.array(z.string()).optional().default([]),
  required_validation_summary_label: z.string().optional().default(""),
  missing_read_contracts: z.array(z.string()),
  missing_read_contract_labels: z.array(z.string()).optional().default([]),
  missing_read_contract_summary_label: z.string().optional().default(""),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([]),
  blocked_claim_summary_label: z.string().optional().default(""),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  action_ids: z.array(z.string()),
  action_summary_label: z.string().optional().default(""),
  apply_allowed: z.boolean(),
  destructive: z.boolean(),
  next_step: z.string()
});

export const AdsBusinessContextReadContractSchema = z.object({
  id: z.string(),
  status: z.enum(["ready", "blocked"]),
  status_label: z.string().default(""),
  title: z.string(),
  summary: z.string(),
  profit_margin: z.number().nullable().optional(),
  business_goal: z.string().nullable().optional(),
  budget_goal: z.string().nullable().optional(),
  target_roas: z.number().nullable().optional(),
  target_cpa_micros: z.number().nullable().optional(),
  strategy_review_status: z
    .enum(["missing", "approved_for_prepare", "needs_changes", "rejected", "deferred"])
    .optional()
    .default("missing"),
  strategy_reviewed_by: z.string().nullable().optional(),
  strategy_reviewed_at: z.string().nullable().optional(),
  strategy_review_summary: z.string().nullable().optional(),
  configured_sources: z.array(z.string()),
  business_policy_ids: z.array(z.string()).optional().default([]),
  operator_review_gates: z.array(z.string()).optional().default([]),
  operator_review_gate_labels: z.array(z.string()).optional().default([]),
  target_interpretation: AdsBusinessTargetInterpretationSchema,
  strategy_review_readiness_contract: AdsStrategyReviewReadinessContractSchema,
  allowed_metrics: z.array(z.string()),
  missing_read_contracts: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  metric_tiles: z.record(z.string(), z.union([z.string(), z.number()])),
  next_step: z.string()
});

export const AdsDerivedKpiRowSchema = z.object({
  campaign_id: z.string().nullable().optional(),
  campaign_name: z.string(),
  ctr: z.number().nullable().optional(),
  average_cpc_micros: z.number().nullable().optional(),
  conversion_rate: z.number().nullable().optional(),
  cost_per_conversion_micros: z.number().nullable().optional(),
  roas: z.number().nullable().optional(),
  value_per_conversion: z.number().nullable().optional(),
  target_roas: z.number().nullable().optional(),
  roas_vs_target: z.number().nullable().optional(),
  target_cpa_micros: z.number().nullable().optional(),
  cpa_vs_target_micros: z.number().nullable().optional(),
  target_status: z
    .enum([
      "within_target",
      "outside_target",
      "spend_without_conversions",
      "insufficient_data",
      "no_target"
    ])
    .default("no_target"),
  target_status_label: z.string().default("brak targetu"),
  target_review_priority: z.number().int().default(90),
  evidence_ids: z.array(z.string()),
  source_metric_names: z.array(z.string()),
  missing_metrics: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([]),
  blocked_claim_summary_label: z.string().optional().default("")
});

export const AdsDerivedKpiReadContractSchema = z.object({
  id: z.string(),
  status: z.enum(["ready", "blocked"]),
  title: z.string(),
  summary: z.string(),
  allowed_metrics: z.array(z.string()),
  missing_read_contracts: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  kpi_rows: z.array(AdsDerivedKpiRowSchema),
  next_step: z.string()
});

export const AdsBudgetApplySafetyReviewSchema = z.object({
  id: z.string(),
  budget_preview_id: z.string(),
  safety_contract: z.literal("campaign_budget_apply_safety_v1"),
  status: z.literal("blocked"),
  status_label: z.string().optional().default(""),
  reason: z.string(),
  max_allowed_delta_percent: z.number(),
  current_budget_amount_micros: z.number().nullable().optional(),
  proposed_budget_amount_micros: z.number().nullable().optional(),
  proposed_delta_percent: z.number().nullable().optional(),
  missing_requirements: z.array(z.string()),
  missing_requirement_labels: z.array(z.string()).optional().default([]),
  required_validation: z.array(z.string()),
  required_validation_labels: z.array(z.string()).optional().default([]),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([]),
  evidence_ids: z.array(z.string()),
  api_mutation_ready: z.boolean(),
  apply_allowed: z.boolean(),
  destructive: z.boolean()
});

export const AdsBudgetApplyPreviewSchema = z.object({
  id: z.string(),
  campaign_id: z.string().nullable().optional(),
  campaign_name: z.string(),
  campaign_budget_id: z.string().nullable().optional(),
  campaign_budget_name: z.string().nullable().optional(),
  operation_type: z.literal("CampaignBudgetOperation"),
  operation_type_label: z.string().optional().default(""),
  current_budget_amount_micros: z.number().nullable().optional(),
  proposed_budget_amount_micros: z.number().nullable().optional(),
  proposed_budget_delta_micros: z.number().nullable().optional(),
  reason: z.string(),
  evidence_ids: z.array(z.string()),
  source_metric_names: z.array(z.string()),
  required_validation: z.array(z.string()),
  required_validation_labels: z.array(z.string()).optional().default([]),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([]),
  safety_review: AdsBudgetApplySafetyReviewSchema,
  api_mutation_ready: z.boolean(),
  apply_allowed: z.boolean(),
  destructive: z.boolean()
});

export const AdsBudgetPacingRowSchema = z.object({
  campaign_id: z.string().nullable().optional(),
  campaign_name: z.string(),
  campaign_status: z.string().nullable().optional(),
  campaign_status_label: z.string().optional().default(""),
  advertising_channel_type: z.string().nullable().optional(),
  advertising_channel_type_label: z.string().optional().default(""),
  budget_id: z.string().nullable().optional(),
  budget_name: z.string().nullable().optional(),
  budget_period: z.string().nullable().optional(),
  budget_period_label: z.string().optional().default(""),
  budget_status: z.string().nullable().optional(),
  budget_status_label: z.string().optional().default(""),
  budget_amount_micros: z.number().nullable().optional(),
  cost_micros_7d: z.number().nullable().optional(),
  seven_day_budget_micros: z.number().nullable().optional(),
  spend_to_budget_ratio_7d: z.number().nullable().optional(),
  has_recommended_budget: z.boolean().nullable().optional(),
  recommended_budget_amount_micros: z.number().nullable().optional(),
  recommended_budget_delta_micros: z.number().nullable().optional(),
  evidence_ids: z.array(z.string()),
  metric_facts: z.array(MetricFactSchema),
  payload_preview: AdsBudgetApplyPreviewSchema.nullable().optional(),
  preview_card: ActionPreviewCardViewModelSchema.nullable().optional(),
  missing_metrics: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([]),
  blocked_claim_summary_label: z.string().optional().default("")
});

export const AdsSharedBudgetCampaignShareSchema = z.object({
  campaign_id: z.string().nullable().optional(),
  campaign_name: z.string(),
  campaign_status: z.string().nullable().optional(),
  campaign_status_label: z.string().optional().default(""),
  advertising_channel_type: z.string().nullable().optional(),
  advertising_channel_type_label: z.string().optional().default(""),
  cost_micros_7d: z.number().nullable().optional(),
  spend_share_7d: z.number().nullable().optional(),
  evidence_ids: z.array(z.string())
});

export const AdsSharedBudgetDistributionRowSchema = z.object({
  budget_id: z.string(),
  budget_name: z.string().nullable().optional(),
  campaign_count: z.number(),
  budget_amount_micros: z.number().nullable().optional(),
  seven_day_budget_micros: z.number().nullable().optional(),
  total_cost_micros_7d: z.number().nullable().optional(),
  spend_to_budget_ratio_7d: z.number().nullable().optional(),
  campaign_shares: z.array(AdsSharedBudgetCampaignShareSchema),
  evidence_ids: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([]),
  blocked_claim_summary_label: z.string().optional().default("")
});

export const AdsBudgetPacingReadContractSchema = z.object({
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
  budget_rows: z.array(AdsBudgetPacingRowSchema),
  shared_budget_distribution_rows: z.array(AdsSharedBudgetDistributionRowSchema)
    .optional()
    .default([]),
  payload_preview: z.array(AdsBudgetApplyPreviewSchema),
  action_ids: z.array(z.string()),
  next_step: z.string()
});
