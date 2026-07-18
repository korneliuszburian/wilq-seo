import { z } from "zod";

import { ConnectorRefreshRunSchema, ConnectorStatusSchema } from "./connectors";
import {
  AdsAccountCurrencyReadContractSchema,
  AdsBlockedHandoffSchema,
  AdsBudgetPacingReadContractSchema,
  AdsBusinessContextReadContractSchema,
  AdsCampaignReadContractSchema,
  AdsCampaignTriageReadContractSchema,
  AdsDerivedKpiReadContractSchema,
  AdsDiagnosticSectionSchema,
  AdsOptimizerReadinessContractSchema
} from "./ads_campaigns";
import {
  AdsImpressionShareReadContractSchema,
  AdsRecommendationsReadContractSchema
} from "./ads_review_contracts";
import {
  AdsChangeHistoryReadContractSchema,
  AdsChangeImpactReadinessContractSchema
} from "./ads_change_history";
import {
  AdsSearchTermNgramReadContractSchema,
  AdsSearchTermReviewSummaryContractSchema,
  AdsSearchTermSafetyReadContractSchema,
  AdsSearchTermsReadContractSchema
} from "./ads_search_terms";
import { AdsKeywordMatchContextReadContractSchema } from "./ads_keyword_contracts";
import { AdsKeywordPlannerReadContractSchema } from "./ads_keyword_planner_contracts";
import { AdsCustomSegmentsReadContractSchema } from "./ads_custom_segments";
import { AdsNegativeKeywordsReadContractSchema } from "./ads_negative_keywords";
import { AdsDecisionItemSchema, AdsOperatorSummarySchema } from "./ads_decisions";

export const AdsFreshnessAssessmentSchema = z.object({
  state: z.enum(["fresh", "stale", "missing", "blocked"]),
  state_label: z.string().default(""),
  checked_at: z.string().nullable().optional(),
  latest_refresh_id: z.string().nullable().optional(),
  latest_refresh_completed_at: z.string().nullable().optional(),
  age_hours: z.number().nullable().optional(),
  stale_after_hours: z.number(),
  requires_refresh: z.boolean(),
  summary: z.string(),
  next_step: z.string()
});

export const AdsAggregationContractSchema = z.object({
  id: z.string(),
  view: z.enum(["full", "summary"]),
  campaign_window: z.string(),
  search_term_windows: z.array(z.string()),
  summary_row_limit: z.number(),
  campaign_rows_returned: z.number(),
  campaign_rows_available: z.number().nullable().optional(),
  search_term_rows_returned: z.number(),
  search_term_rows_available: z.number().nullable().optional(),
  is_exhaustive: z.boolean(),
  summary_scope: z.string(),
  pacing_basis: z.string(),
  currency_code: z.string().nullable().optional(),
  currency_status: z.enum(["ready", "blocked", "missing"]),
  money_aggregation_allowed: z.boolean(),
  caveats: z.array(z.string())
});

export const AdsDiagnosticsResponseSchema = z.object({
  generated_at: z.string().nullable().optional(),
  language: z.literal("pl-PL"),
  strict_instruction: z.string(),
  connector: ConnectorStatusSchema,
  connector_status_label: z.string().default(""),
  latest_refresh: ConnectorRefreshRunSchema.nullable().optional(),
  latest_refresh_status_label: z.string().nullable().optional(),
  live_data_status_label: z.string().default(""),
  live_data_available: z.boolean(),
  freshness_assessment: AdsFreshnessAssessmentSchema,
  aggregation_contract: AdsAggregationContractSchema,
  campaign_read_contract: AdsCampaignReadContractSchema,
  account_currency_read_contract: AdsAccountCurrencyReadContractSchema,
  business_context_read_contract: AdsBusinessContextReadContractSchema,
  derived_kpi_read_contract: AdsDerivedKpiReadContractSchema,
  budget_pacing_read_contract: AdsBudgetPacingReadContractSchema,
  recommendations_read_contract: AdsRecommendationsReadContractSchema,
  impression_share_read_contract: AdsImpressionShareReadContractSchema,
  campaign_triage_read_contract: AdsCampaignTriageReadContractSchema,
  optimizer_readiness_contract: AdsOptimizerReadinessContractSchema,
  change_history_read_contract: AdsChangeHistoryReadContractSchema,
  change_impact_readiness_contract: AdsChangeImpactReadinessContractSchema,
  search_terms_read_contract: AdsSearchTermsReadContractSchema,
  search_term_review_summary_contract: AdsSearchTermReviewSummaryContractSchema,
  search_term_ngram_read_contract: AdsSearchTermNgramReadContractSchema,
  search_term_safety_read_contract: AdsSearchTermSafetyReadContractSchema,
  keyword_match_context_read_contract: AdsKeywordMatchContextReadContractSchema,
  keyword_planner_read_contract: AdsKeywordPlannerReadContractSchema,
  custom_segments_read_contract: AdsCustomSegmentsReadContractSchema,
  negative_keywords_read_contract: AdsNegativeKeywordsReadContractSchema,
  operator_summary: AdsOperatorSummarySchema,
  decision_queue: z.array(AdsDecisionItemSchema),
  sections: z.array(AdsDiagnosticSectionSchema),
  blocked_handoff: AdsBlockedHandoffSchema.nullable().optional(),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  source_connector_labels: z.array(z.string()).default([]),
  action_ids: z.array(z.string()),
  action_summary_label: z.string().default(""),
  blocker_count: z.number()
});
