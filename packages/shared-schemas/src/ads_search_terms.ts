import { z } from "zod";

import { MetricFactSchema } from "./connectors";

export const AdsSearchTermMetricRowSchema = z.object({
  search_term: z.string(),
  campaign_id: z.string().nullable().optional(),
  campaign_name: z.string().nullable().optional(),
  campaign_label: z.string().optional().default(""),
  ad_group_id: z.string().nullable().optional(),
  ad_group_name: z.string().nullable().optional(),
  ad_group_label: z.string().optional().default(""),
  search_term_status: z.string().nullable().optional(),
  clicks: z.number().nullable().optional(),
  impressions: z.number().nullable().optional(),
  cost_micros: z.number().nullable().optional(),
  conversions: z.number().nullable().optional(),
  conversion_value: z.number().nullable().optional(),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  metric_facts: z.array(MetricFactSchema),
  missing_metrics: z.array(z.string()),
  blocked_claims: z.array(z.string())
});

export const AdsSearchTermsReadContractSchema = z.object({
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
  search_term_rows: z.array(AdsSearchTermMetricRowSchema),
  next_step: z.string()
});

export const AdsSearchTermReviewRowSchema = z.object({
  search_term: z.string(),
  campaign_id: z.string().nullable().optional(),
  campaign_name: z.string().nullable().optional(),
  campaign_label: z.string().optional().default(""),
  ad_group_id: z.string().nullable().optional(),
  ad_group_name: z.string().nullable().optional(),
  ad_group_label: z.string().optional().default(""),
  search_term_status: z.string().nullable().optional(),
  clicks: z.number().nullable().optional(),
  impressions: z.number().nullable().optional(),
  cost_micros: z.number().nullable().optional(),
  conversions: z.number().nullable().optional(),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  blocked_claims: z.array(z.string())
});

export const AdsSearchTermCampaignReviewRowSchema = z.object({
  campaign_id: z.string().nullable().optional(),
  campaign_name: z.string().nullable().optional(),
  campaign_label: z.string().optional().default(""),
  search_term_count: z.number().int().nonnegative(),
  zero_conversion_search_term_count: z.number().int().nonnegative(),
  clicks: z.number().int().nonnegative(),
  impressions: z.number().int().nonnegative(),
  cost_micros: z.number().int().nonnegative(),
  conversions: z.number(),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  blocked_claims: z.array(z.string())
});

export const AdsSearchTermReviewSummaryContractSchema = z.object({
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
  total_search_term_count: z.number().int().nonnegative(),
  zero_conversion_search_term_count: z.number().int().nonnegative(),
  total_clicks: z.number().int().nonnegative(),
  total_impressions: z.number().int().nonnegative(),
  total_cost_micros: z.number().int().nonnegative(),
  total_conversions: z.number(),
  top_cost_search_terms: z.array(AdsSearchTermReviewRowSchema),
  campaign_review_rows: z.array(AdsSearchTermCampaignReviewRowSchema),
  next_step: z.string()
});

export const AdsSearchTermNgramRowSchema = z.object({
  ngram: z.string(),
  ngram_size: z.number().min(1).max(3),
  source_search_term_count: z.number(),
  sample_search_terms: z.array(z.string()),
  clicks: z.number().nullable().optional(),
  impressions: z.number().nullable().optional(),
  cost_micros: z.number().nullable().optional(),
  conversions: z.number().nullable().optional(),
  conversion_value: z.number().nullable().optional(),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  metric_facts: z.array(MetricFactSchema),
  missing_metrics: z.array(z.string()),
  blocked_claims: z.array(z.string())
});

export const AdsSearchTermNgramReadContractSchema = z.object({
  id: z.string(),
  status: z.enum(["ready", "blocked"]),
  title: z.string(),
  summary: z.string(),
  allowed_metrics: z.array(z.string()),
  missing_read_contracts: z.array(z.string()),
  operator_review_gates: z.array(z.string()).optional().default([]),
  operator_review_gate_labels: z.array(z.string()).optional().default([]),
  blocked_claims: z.array(z.string()),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  action_ids: z.array(z.string()).optional().default([]),
  ngram_rows: z.array(AdsSearchTermNgramRowSchema),
  next_step: z.string()
});

export const AdsSearchTermSafetyRowSchema = z.object({
  search_term: z.string(),
  campaign_id: z.string().nullable().optional(),
  campaign_name: z.string().nullable().optional(),
  campaign_label: z.string().optional().default(""),
  ad_group_id: z.string().nullable().optional(),
  ad_group_name: z.string().nullable().optional(),
  ad_group_label: z.string().optional().default(""),
  search_term_status: z.string().nullable().optional(),
  clicks_90d: z.number().nullable().optional(),
  impressions_90d: z.number().nullable().optional(),
  cost_micros_90d: z.number().nullable().optional(),
  conversions_90d: z.number().nullable().optional(),
  conversion_value_90d: z.number().nullable().optional(),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  metric_facts: z.array(MetricFactSchema),
  missing_metrics: z.array(z.string()),
  blocked_claims: z.array(z.string())
});

export const AdsSearchTermSafetyReadContractSchema = z.object({
  id: z.string(),
  status: z.enum(["ready", "blocked"]),
  title: z.string(),
  summary: z.string(),
  allowed_metrics: z.array(z.string()),
  missing_read_contracts: z.array(z.string()),
  operator_review_gates: z.array(z.string()).optional().default([]),
  operator_review_gate_labels: z.array(z.string()).optional().default([]),
  blocked_claims: z.array(z.string()),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  safety_rows: z.array(AdsSearchTermSafetyRowSchema),
  next_step: z.string()
});
