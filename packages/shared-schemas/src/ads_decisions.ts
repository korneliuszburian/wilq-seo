import { z } from "zod";

import { MetricFactSchema } from "./connectors";
import {
  AdsBudgetApplyPreviewSchema,
  AdsBudgetPacingRowSchema,
  AdsCampaignMetricRowSchema,
  AdsCampaignTriageRowSchema,
  AdsDerivedKpiRowSchema,
  AdsSharedBudgetDistributionRowSchema
} from "./ads_campaigns";
import {
  AdsImpressionShareRowSchema,
  AdsRecommendationApplyPreviewSchema,
  AdsRecommendationRowSchema
} from "./ads_review_contracts";
import { AdsChangeHistoryRowSchema } from "./ads_change_history";
import {
  AdsSearchTermMetricRowSchema,
  AdsSearchTermNgramRowSchema,
  AdsSearchTermSafetyRowSchema
} from "./ads_search_terms";
import { AdsKeywordMatchContextRowSchema } from "./ads_keyword_contracts";
import { AdsKeywordPlannerIdeaRowSchema } from "./ads_keyword_planner_contracts";
import {
  AdsCustomSegmentAudienceForecastRowSchema,
  AdsCustomSegmentCandidateSchema,
  AdsCustomSegmentPayloadPreviewSchema
} from "./ads_custom_segments";
import {
  AdsNegativeKeywordCandidateSchema,
  AdsNegativeKeywordPayloadPreviewSchema
} from "./ads_negative_keywords";

export const AdsDecisionItemSchema = z.object({
  id: z.string(),
  decision_type: z.enum([
    "review_campaign_activity",
    "review_business_context",
    "review_derived_kpi",
    "review_budget_context",
    "review_recommendations",
    "review_impression_share",
    "review_change_history",
    "review_campaign_triage",
    "review_search_term_safety",
    "review_search_terms",
    "review_search_term_ngrams",
    "review_negative_keyword_safety",
    "prepare_custom_segments",
    "block_write_actions",
    "fix_ads_access"
  ]),
  status: z.enum(["ready", "blocked"]),
  status_label: z.string().default(""),
  decision_type_label: z.string().default(""),
  title: z.string(),
  summary: z.string(),
  start_here_summary: z.string().default(""),
  measurement_plan: z.string().default(""),
  rationale: z.string(),
  next_step: z.string(),
  priority: z.number().default(50),
  priority_label: z.string().default(""),
  metric_tiles: z.record(z.string(), z.union([z.string(), z.number()])).default({}),
  allowed_metrics: z.array(z.string()),
  missing_read_contracts: z.array(z.string()),
  missing_read_contract_labels: z.array(z.string()).default([]),
  missing_read_contract_summary_label: z.string().optional().default(""),
  operator_review_gates: z.array(z.string()).optional().default([]),
  operator_review_gate_labels: z.array(z.string()).optional().default([]),
  operator_review_gate_summary_label: z.string().optional().default(""),
  source_connectors: z.array(z.string()),
  source_connector_labels: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  metric_facts: z.array(MetricFactSchema),
  campaign_rows: z.array(AdsCampaignMetricRowSchema),
  campaign_triage_rows: z.array(AdsCampaignTriageRowSchema).optional().default([]),
  derived_kpi_rows: z.array(AdsDerivedKpiRowSchema),
  budget_rows: z.array(AdsBudgetPacingRowSchema),
  shared_budget_distribution_rows: z.array(AdsSharedBudgetDistributionRowSchema)
    .optional()
    .default([]),
  budget_apply_preview: z.array(AdsBudgetApplyPreviewSchema).optional().default([]),
  recommendation_rows: z.array(AdsRecommendationRowSchema),
  recommendation_apply_preview: z.array(AdsRecommendationApplyPreviewSchema)
    .optional()
    .default([]),
  impression_share_rows: z.array(AdsImpressionShareRowSchema),
  change_history_rows: z.array(AdsChangeHistoryRowSchema),
  search_term_rows: z.array(AdsSearchTermMetricRowSchema),
  search_term_ngram_rows: z.array(AdsSearchTermNgramRowSchema)
    .optional()
    .default([]),
  search_term_safety_rows: z.array(AdsSearchTermSafetyRowSchema),
  keyword_match_context_rows: z.array(AdsKeywordMatchContextRowSchema)
    .optional()
    .default([]),
  keyword_planner_idea_rows: z.array(AdsKeywordPlannerIdeaRowSchema)
    .optional()
    .default([]),
  custom_segment_candidates: z.array(AdsCustomSegmentCandidateSchema),
  custom_segment_payload_preview: z.array(AdsCustomSegmentPayloadPreviewSchema)
    .optional()
    .default([]),
  custom_segment_audience_forecast_rows: z
    .array(AdsCustomSegmentAudienceForecastRowSchema)
    .optional()
    .default([]),
  negative_keyword_candidates: z.array(AdsNegativeKeywordCandidateSchema),
  negative_keyword_payload_preview: z.array(AdsNegativeKeywordPayloadPreviewSchema),
  action_ids: z.array(z.string()),
  action_summary_label: z.string().default(""),
  knowledge_card_ids: z.array(z.string()).optional().default([]),
  expert_rule_ids: z.array(z.string()).optional().default([]),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).default([]),
  blocked_claim_summary_label: z.string().optional().default(""),
  risk_label: z.string().default(""),
  risk: z.enum(["low", "medium", "high", "critical"])
});

export const AdsOperatorSummarySchema = z.object({
  id: z.literal("ads_operator_summary"),
  title: z.string(),
  summary: z.string(),
  next_step: z.string(),
  review_card_label: z.string().default("Karta review Localo"),
  review_decision_after_review: z.string().default(""),
  review_question_for_operator: z.string().default(""),
  review_next_safe_click: z.string().default(""),
  review_action_ids: z.array(z.string()).default([]),
  top_decision_ids: z.array(z.string()),
  campaign_count: z.number(),
  search_term_count: z.number(),
  total_clicks: z.number(),
  total_impressions: z.number(),
  total_cost_micros: z.number(),
  total_conversions: z.number(),
  total_conversion_value: z.number(),
  ready_area_count: z.number(),
  blocked_area_count: z.number(),
  allowed_metrics: z.array(z.string()),
  allowed_metric_labels: z.array(z.string()).default([]),
  missing_read_contracts: z.array(z.string()),
  missing_read_contract_labels: z.array(z.string()).default([]),
  missing_read_contract_summary_label: z.string().optional().default(""),
  operator_review_gates: z.array(z.string()),
  operator_review_gate_labels: z.array(z.string()).optional().default([]),
  operator_review_gate_summary_label: z.string().optional().default(""),
  source_connectors: z.array(z.string()),
  source_connector_labels: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  action_ids: z.array(z.string()),
  action_summary_label: z.string().default(""),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).default([]),
  blocked_claim_summary_label: z.string().optional().default(""),
  top_blocked_claim_labels: z.array(z.string()).default([]),
  top_blocked_claim_summary_label: z.string().optional().default("")
});


