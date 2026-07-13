import { z } from "zod";

import { MetricFactSchema } from "./connectors";

export const AdsKeywordMatchContextRowSchema = z.object({
  keyword_text: z.string(),
  match_type: z.string(),
  match_type_label: z.string().optional().default(""),
  criterion_id: z.string().nullable().optional(),
  criterion_status: z.string().nullable().optional(),
  criterion_status_label: z.string().optional().default(""),
  negative: z.boolean().nullable().optional(),
  negative_label: z.string().optional().default(""),
  campaign_id: z.string().nullable().optional(),
  campaign_name: z.string().nullable().optional(),
  campaign_label: z.string().optional().default(""),
  ad_group_id: z.string().nullable().optional(),
  ad_group_name: z.string().nullable().optional(),
  ad_group_label: z.string().optional().default(""),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  metric_facts: z.array(MetricFactSchema),
  blocked_claims: z.array(z.string())
});

export const AdsKeywordMatchContextReadContractSchema = z.object({
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
  context_rows: z.array(AdsKeywordMatchContextRowSchema),
  next_step: z.string()
});
