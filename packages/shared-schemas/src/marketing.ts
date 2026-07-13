import { z } from "zod";

import { ConnectorSummarySchema, MetricFactSchema } from "./connectors";

export const MarketingBriefItemSchema = z.object({
  id: z.string(),
  title: z.string(),
  kind: z.enum(["metric", "blocker", "action", "recommendation"]),
  kind_label: z.string().default(""),
  priority: z.number(),
  priority_label: z.string().default(""),
  source_connectors: z.array(z.string()),
  source_connector_labels: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  metric_facts: z.array(MetricFactSchema),
  metric_fact_labels: z.record(z.string(), z.string()).default({}),
  action_ids: z.array(z.string()),
  action_summary_label: z.string().default(""),
  summary: z.string(),
  next_step: z.string(),
  risk: z.string(),
  risk_label: z.string().default(""),
  blocker_reason: z.string().nullable().optional()
});

export const MarketingBriefSectionSchema = z.object({
  id: z.string(),
  title: z.string(),
  description: z.string(),
  items: z.array(MarketingBriefItemSchema)
});

export const MarketingBriefSchema = z.object({
  generated_at: z.string().nullable().optional(),
  language: z.literal("pl-PL"),
  strict_instruction: z.string(),
  connector_summary: ConnectorSummarySchema,
  sections: z.array(MarketingBriefSectionSchema),
  top_metric_facts: z.array(MetricFactSchema),
  evidence_ids: z.array(z.string()),
  action_ids: z.array(z.string()),
  blocker_count: z.number(),
  recommendation_count: z.number()
});

export const TacticalQueueItemSchema = z.object({
  id: z.string(),
  title: z.string(),
  domain: z.string(),
  domain_label: z.string().default(""),
  intent: z.enum([
    "content_refresh",
    "content_create",
    "content_merge",
    "content_block",
    "landing_page_quality",
    "tracking_gap",
    "merchant_feed_triage",
    "traffic_quality_review"
  ]),
  intent_label: z.string().default(""),
  priority: z.number(),
  priority_label: z.string().default(""),
  risk: z.enum(["low", "medium", "high", "critical"]),
  risk_label: z.string().default(""),
  source_connectors: z.array(z.string()),
  source_connector_labels: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  metric_facts: z.array(MetricFactSchema),
  dimensions: z.record(z.string(), z.string()).optional().default({}),
  dimension_labels: z.record(z.string(), z.string()).optional().default({}),
  dimension_value_labels: z.record(z.string(), z.string()).optional().default({}),
  diagnosis: z.string(),
  next_step: z.string(),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).default([]),
  action_ids: z.array(z.string()).default([]),
  action_summary_label: z.string().default("")
});

export const TacticalQueueGroupSchema = z.object({
  id: z.string(),
  title: z.string(),
  meta: z.string(),
  diagnosis: z.string(),
  next_step: z.string(),
  priority: z.number(),
  priority_label: z.string().default(""),
  risk: z.enum(["low", "medium", "high", "critical"]),
  risk_label: z.string().default(""),
  source_connectors: z.array(z.string()),
  source_connector_labels: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  action_ids: z.array(z.string()),
  action_summary_label: z.string().default(""),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).default([])
});

export const TacticalQueueResponseSchema = z.object({
  generated_at: z.string().nullable().optional(),
  language: z.literal("pl-PL"),
  strict_instruction: z.string(),
  items: z.array(TacticalQueueItemSchema),
  compact_groups: z.array(TacticalQueueGroupSchema).optional().default([]),
  evidence_ids: z.array(z.string()),
  action_ids: z.array(z.string())
});

export type MarketingBrief = z.infer<typeof MarketingBriefSchema>;
export type MarketingBriefItem = z.infer<typeof MarketingBriefItemSchema>;
export type MarketingBriefSection = z.infer<typeof MarketingBriefSectionSchema>;
export type TacticalQueueItem = z.infer<typeof TacticalQueueItemSchema>;
export type TacticalQueueResponse = z.infer<typeof TacticalQueueResponseSchema>;
