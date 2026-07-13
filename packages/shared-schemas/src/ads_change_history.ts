import { z } from "zod";

import { MetricFactSchema } from "./connectors";


export const AdsChangeHistoryRowSchema = z.object({
  change_event_id: z.string().nullable().optional(),
  change_date_time: z.string().nullable().optional(),
  change_resource_id: z.string().nullable().optional(),
  change_resource_type: z.string().nullable().optional(),
  change_resource_type_label: z.string().optional().default(""),
  change_resource_label: z.string().optional().default(""),
  resource_change_operation: z.string().nullable().optional(),
  resource_change_operation_label: z.string().optional().default(""),
  client_type: z.string().nullable().optional(),
  client_type_label: z.string().optional().default(""),
  campaign_id: z.string().nullable().optional(),
  campaign_label: z.string().optional().default(""),
  changed_field_count: z.number().nullable().optional(),
  changed_fields: z.array(z.string()),
  changed_field_labels: z.array(z.string()).optional().default([]),
  changed_field_summary_label: z.string().optional().default(""),
  evidence_ids: z.array(z.string()),
  metric_facts: z.array(MetricFactSchema),
  missing_metrics: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([])
});

export const AdsChangeHistoryReadContractSchema = z.object({
  id: z.string(),
  status: z.enum(["ready", "blocked"]),
  status_label: z.string().optional().default(""),
  title: z.string(),
  summary: z.string(),
  allowed_metrics: z.array(z.string()),
  allowed_metric_labels: z.array(z.string()).optional().default([]),
  missing_read_contracts: z.array(z.string()),
  missing_read_contract_labels: z.array(z.string()).optional().default([]),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([]),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  change_history_rows: z.array(AdsChangeHistoryRowSchema),
  action_ids: z.array(z.string()).optional().default([]),
  next_step: z.string()
});

export const AdsChangeImpactReadinessRowSchema = z.object({
  change_event_id: z.string().nullable().optional(),
  change_event_label: z.string().optional().default(""),
  campaign_id: z.string().nullable().optional(),
  campaign_name: z.string().nullable().optional(),
  campaign_label: z.string().optional().default(""),
  change_date_time: z.string().nullable().optional(),
  changed_fields: z.array(z.string()),
  changed_field_labels: z.array(z.string()).optional().default([]),
  current_campaign_metrics_available: z.boolean(),
  pre_window_available: z.boolean(),
  post_window_available: z.boolean(),
  current_clicks: z.number().nullable().optional(),
  current_impressions: z.number().nullable().optional(),
  current_cost_micros: z.number().nullable().optional(),
  current_conversions: z.number().nullable().optional(),
  current_conversion_value: z.number().nullable().optional(),
  missing_read_contracts: z.array(z.string()),
  missing_read_contract_labels: z.array(z.string()).optional().default([]),
  missing_read_contract_summary_label: z.string().optional().default(""),
  evidence_ids: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([]),
  blocked_claim_summary_label: z.string().optional().default("")
});

export const AdsChangeImpactReadinessContractSchema = z.object({
  id: z.string(),
  status: z.enum(["ready", "blocked"]),
  status_label: z.string().optional().default(""),
  title: z.string(),
  summary: z.string(),
  allowed_metrics: z.array(z.string()),
  allowed_metric_labels: z.array(z.string()).optional().default([]),
  missing_read_contracts: z.array(z.string()),
  missing_read_contract_labels: z.array(z.string()).optional().default([]),
  missing_read_contract_summary_label: z.string().optional().default(""),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([]),
  blocked_claim_summary_label: z.string().optional().default(""),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  readiness_rows: z.array(AdsChangeImpactReadinessRowSchema),
  action_ids: z.array(z.string()).optional().default([]),
  action_summary_label: z.string().optional().default(""),
  api_mutation_ready: z.boolean(),
  apply_allowed: z.boolean(),
  next_step: z.string()
});


