import { z } from "zod";

import { MetricFactSchema } from "./connectors";

export const AdsKeywordPlannerIdeaRowSchema = z.object({
  idea_text: z.string(),
  avg_monthly_searches: z.number().nullable().optional(),
  competition: z.string().nullable().optional(),
  competition_index: z.number().nullable().optional(),
  low_top_of_page_bid_micros: z.number().nullable().optional(),
  high_top_of_page_bid_micros: z.number().nullable().optional(),
  source_terms: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  metric_facts: z.array(MetricFactSchema),
  missing_metrics: z.array(z.string()),
  blocked_claims: z.array(z.string())
});

export const AdsKeywordPlannerReadContractSchema = z.object({
  id: z.string(),
  status: z.enum(["ready", "blocked"]),
  status_label: z.string().default(""),
  title: z.string(),
  summary: z.string(),
  allowed_metrics: z.array(z.string()),
  missing_read_contracts: z.array(z.string()),
  operator_review_gates: z.array(z.string()).optional().default([]),
  operator_review_gate_labels: z.array(z.string()).optional().default([]),
  blocked_claims: z.array(z.string()),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  idea_rows: z.array(AdsKeywordPlannerIdeaRowSchema),
  next_step: z.string()
});
