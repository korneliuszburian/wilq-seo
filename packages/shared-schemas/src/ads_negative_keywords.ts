import { z } from "zod";

import { ActionPreviewCardViewModelSchema } from "./actions";
import { AdsKeywordMatchContextRowSchema } from "./ads_keyword_contracts";
import { MetricFactSchema } from "./connectors";

export const AdsNegativeKeywordPayloadPreviewSchema = z.object({
  id: z.string(),
  search_term: z.string(),
  negative_keyword_text: z.string(),
  match_type: z.literal("EXACT"),
  match_type_label: z.string().optional().default(""),
  level: z.enum(["ad_group", "campaign_review_required"]),
  level_label: z.string().optional().default(""),
  campaign_id: z.string().nullable().optional(),
  campaign_name: z.string().nullable().optional(),
  campaign_label: z.string().optional().default(""),
  ad_group_id: z.string().nullable().optional(),
  ad_group_name: z.string().nullable().optional(),
  ad_group_label: z.string().optional().default(""),
  reason: z.string(),
  evidence_ids: z.array(z.string()),
  safety_evidence_ids: z.array(z.string()),
  source_metric_names: z.array(z.string()),
  required_validation: z.array(z.string()),
  required_validation_labels: z.array(z.string()).optional().default([]),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([]),
  api_mutation_ready: z.boolean(),
  apply_allowed: z.boolean(),
  destructive: z.boolean()
});

export const AdsNegativeKeywordCandidateSchema = z.object({
  id: z.string(),
  search_term: z.string(),
  review_priority: z
    .enum(["pilne", "wysokie", "normalne", "niski sygnał"])
    .default("normalne"),
  review_score: z.number().min(0).max(100).default(0),
  review_reason: z.string(),
  human_review_gates: z.array(z.string()).default([]),
  human_review_gate_labels: z.array(z.string()).optional().default([]),
  campaign_id: z.string().nullable().optional(),
  campaign_name: z.string().nullable().optional(),
  campaign_label: z.string().optional().default(""),
  ad_group_id: z.string().nullable().optional(),
  ad_group_name: z.string().nullable().optional(),
  ad_group_label: z.string().optional().default(""),
  clicks: z.number().nullable().optional(),
  impressions: z.number().nullable().optional(),
  cost_micros: z.number().nullable().optional(),
  conversions: z.number().nullable().optional(),
  conversion_value: z.number().nullable().optional(),
  clicks_90d: z.number().nullable().optional(),
  impressions_90d: z.number().nullable().optional(),
  cost_micros_90d: z.number().nullable().optional(),
  conversions_90d: z.number().nullable().optional(),
  conversion_value_90d: z.number().nullable().optional(),
  evidence_ids: z.array(z.string()),
  safety_evidence_ids: z.array(z.string()),
  keyword_context_evidence_ids: z.array(z.string()).optional().default([]),
  metric_facts: z.array(MetricFactSchema),
  safety_metric_facts: z.array(MetricFactSchema),
  keyword_context_rows: z.array(AdsKeywordMatchContextRowSchema).optional().default([]),
  payload_preview: AdsNegativeKeywordPayloadPreviewSchema.nullable().optional(),
  preview_card: ActionPreviewCardViewModelSchema.nullable().optional(),
  required_checks: z.array(z.string()),
  required_check_labels: z.array(z.string()).optional().default([]),
  safety_status: z.enum(["needs_90_day_review", "read_ready_needs_human_review", "blocked"]),
  safety_status_label: z.string().optional().default(""),
  validation_status: z.enum(["pending_validation", "blocked"]),
  validation_status_label: z.string().optional().default(""),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([]),
  next_step: z.string()
});

export const AdsNegativeKeywordsReadContractSchema = z.object({
  id: z.string(),
  status: z.enum(["ready", "blocked"]),
  title: z.string(),
  summary: z.string(),
  candidates: z.array(AdsNegativeKeywordCandidateSchema),
  payload_preview: z.array(AdsNegativeKeywordPayloadPreviewSchema),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  missing_read_contracts: z.array(z.string()),
  missing_read_contract_labels: z.array(z.string()).optional().default([]),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([]),
  action_ids: z.array(z.string()),
  next_step: z.string()
});

