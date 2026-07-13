import { z } from "zod";

import { ActionPreviewCardViewModelSchema } from "./actions";
import { AdsCampaignMetricRowSchema } from "./ads_campaigns";

export const DemandGenReadinessContractSchema = z.object({
  status: z.enum(["ready", "blocked"]),
  status_label: z.string().default(""),
  title: z.string(),
  summary: z.string(),
  metric_tiles: z.record(z.string(), z.union([z.string(), z.number()])).default({}),
  available_read_contracts: z.array(z.string()),
  available_read_contract_labels: z.array(z.string()).optional().default([]),
  missing_read_contracts: z.array(z.string()),
  missing_read_contract_labels: z.array(z.string()).optional().default([]),
  blocked_claims: z.array(z.string()),
  source_connectors: z.array(z.string()),
  source_connector_labels: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  action_ids: z.array(z.string()),
  action_summary_label: z.string().default(""),
  operator_review_gates: z.array(z.string()),
  operator_review_gate_labels: z.array(z.string()).optional().default([]),
  payload_preview: z.array(z.record(z.string(), z.unknown())).default([]),
  preview_cards: z.array(ActionPreviewCardViewModelSchema).default([]),
  campaign_rows_evaluated: z.number(),
  campaign_channel_counts: z.record(z.string(), z.number()),
  campaign_channel_labels: z.record(z.string(), z.string()).optional().default({}),
  demand_gen_campaign_rows: z.array(AdsCampaignMetricRowSchema),
  demand_gen_ad_group_ad_rows: z.array(z.object({
    campaign_id: z.string().nullable().optional(),
    campaign_name: z.string().nullable().optional(),
    campaign_status: z.string().nullable().optional(),
    advertising_channel_type: z.string().nullable().optional(),
    ad_group_id: z.string().nullable().optional(),
    ad_group_name: z.string().nullable().optional(),
    ad_id: z.string().nullable().optional(),
    ad_type: z.string().nullable().optional(),
    ad_status: z.string().nullable().optional(),
    final_url_count: z.number().default(0),
    asset_reference_count: z.number().default(0),
    evidence_ids: z.array(z.string()).default([]),
    evidence_summary_label: z.string().default("")
  })).default([]),
  demand_gen_creative_asset_rows: z.array(z.object({
    asset_id: z.string().nullable().optional(),
    asset_type: z.string().nullable().optional(),
    field_type: z.string().nullable().optional(),
    impressions: z.number().nullable().optional(),
    evidence_ids: z.array(z.string()).default([]),
    evidence_summary_label: z.string().default("")
  })).default([]),
  demand_gen_landing_quality_rows: z.array(z.object({
    campaign_id: z.string().nullable().optional(),
    campaign_name: z.string(),
    landing_page: z.string(),
    landing_page_label: z.string().default(""),
    source_medium: z.string().nullable().optional(),
    source_medium_label: z.string().default(""),
    active_users: z.number().nullable().optional(),
    active_users_label: z.string().default(""),
    sessions: z.number().nullable().optional(),
    sessions_label: z.string().default(""),
    engagement_rate: z.number().nullable().optional(),
    engagement_rate_label: z.string().default(""),
    evidence_ids: z.array(z.string()).default([]),
    evidence_summary_label: z.string().default("")
  })).default([]),
  demand_gen_campaign_mode_review_rows: z.array(z.object({
    campaign_id: z.string().nullable().optional(),
    campaign_name: z.string(),
    campaign_status: z.string().nullable().optional(),
    campaign_status_label: z.string().optional().default(""),
    advertising_channel_type: z.string().nullable().optional(),
    advertising_channel_type_label: z.string().optional().default(""),
    review_required: z.boolean().default(false),
    review_status_label: z.string().default(""),
    reason: z.string(),
    reason_label: z.string().nullable().optional(),
    evidence_ids: z.array(z.string()).default([]),
    evidence_summary_label: z.string().default("")
  })).default([]),
  next_step: z.string(),
  risk: z.enum(["low", "medium", "high"]),
  risk_label: z.string().default("")
});


