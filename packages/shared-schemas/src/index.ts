import { z } from "zod";

export const ConnectorStatusSchema = z.object({
  id: z.string(),
  label: z.string(),
  status: z.string(),
  configured: z.boolean(),
  missing_credentials: z.array(z.string()),
  available_credential_sources: z.array(z.string()),
  freshness: z.object({
    state: z.string(),
    notes: z.string().nullable().optional()
  }),
  supported_actions: z.array(z.string())
});

export const MetricFactSchema = z.object({
  name: z.string(),
  value: z.union([z.string(), z.number()]),
  period: z.string(),
  source_connector: z.string(),
  evidence_id: z.string(),
  dimensions: z.record(z.string()).optional().default({}),
  unit: z.string().nullable().optional(),
  collected_at: z.string().nullable().optional(),
  previous_value: z.union([z.string(), z.number()]).nullable().optional(),
  delta: z.number().nullable().optional(),
  delta_percent: z.number().nullable().optional(),
  trend: z.enum(["up", "down", "flat", "unknown"]).optional(),
  freshness_state: z.enum(["fresh", "stale", "unknown"]).optional(),
  freshness_label: z.string().nullable().optional()
});

export const MetricStoreStatusSchema = z.object({
  backend: z.string(),
  enabled: z.boolean(),
  path_configured: z.boolean(),
  metric_fact_count: z.number(),
  connector_count: z.number(),
  refresh_run_count: z.number()
});

export const EvidenceSchema = z.object({
  id: z.string(),
  source_connector: z.string(),
  source_type: z.string(),
  source_id: z.string(),
  collected_at: z.string(),
  freshness: z.object({
    state: z.string(),
    notes: z.string().nullable().optional()
  }),
  summary: z.string(),
  raw_ref: z.string().nullable().optional()
});

export const ConnectorRefreshRunSchema = z.object({
  id: z.string(),
  connector_id: z.string(),
  mode: z.enum(["status_probe", "vendor_read"]),
  status: z.enum(["completed", "blocked", "failed"]),
  started_at: z.string(),
  completed_at: z.string().nullable().optional(),
  evidence_ids: z.array(z.string()),
  missing_credentials: z.array(z.string()),
  checked_credentials: z.array(z.string()),
  external_call_attempted: z.boolean(),
  vendor_data_collected: z.boolean(),
  metric_summary: z.record(z.union([z.string(), z.number()])),
  summary: z.string(),
  errors: z.array(z.string()),
  redacted: z.boolean()
});

export const OpportunitySchema = z.object({
  id: z.string(),
  type: z.string(),
  title: z.string(),
  domain: z.string(),
  source_connectors: z.array(z.string()).min(1),
  evidence_ids: z.array(z.string()).min(1),
  metric_tiles: z.record(z.union([z.string(), z.number()])).default({}),
  metrics: z.array(MetricFactSchema),
  human_diagnosis: z.string().min(1),
  recommended_action: z.string(),
  risk: z.string(),
  action_ids: z.array(z.string()),
  expert_rule_ids: z.array(z.string()),
  playbook_ids: z.array(z.string()),
  is_fixture: z.boolean()
});

export const AuditEventSchema = z.object({
  id: z.string(),
  action_id: z.string().nullable().optional(),
  event_type: z.string(),
  actor: z.string(),
  created_at: z.string(),
  summary: z.string(),
  evidence_ids: z.array(z.string()),
  redacted: z.boolean()
});

export const ActionReviewOutcomeSchema = z.enum([
  "approved_for_prepare",
  "needs_changes",
  "rejected",
  "deferred"
]);

export const ActionReviewRequestSchema = z.object({
  outcome: ActionReviewOutcomeSchema,
  reviewed_by: z.string().min(1),
  notes: z.string().min(1).max(2000),
  checked_items: z.array(z.string()).default([]),
  blockers: z.array(z.string()).default([])
});

export const ActionReviewGateSchema = z.object({
  status: z
    .enum(["pending_validation", "validated_prepare_only", "ready_to_apply", "blocked_apply"])
    .default("pending_validation"),
  summary: z.string().default("Wymaga walidacji ActionObject przed kolejnym krokiem."),
  required_checks: z.array(z.string()).default([]),
  operator_checklist: z.array(z.string()).default([]),
  apply_blockers: z.array(z.string()).default([]),
  confirmation_required: z.boolean().default(true),
  apply_allowed: z.boolean().default(false),
  last_review_outcome: ActionReviewOutcomeSchema.nullable().optional(),
  last_reviewed_by: z.string().nullable().optional(),
  last_reviewed_at: z.string().nullable().optional(),
  last_review_summary: z.string().nullable().optional(),
  last_confirmation_by: z.string().nullable().optional(),
  last_confirmation_at: z.string().nullable().optional(),
  last_confirmation_summary: z.string().nullable().optional(),
  last_impact_check_status: z.enum(["checked", "blocked"]).nullable().optional(),
  last_impact_checked_by: z.string().nullable().optional(),
  last_impact_checked_at: z.string().nullable().optional(),
  last_impact_check_summary: z.string().nullable().optional(),
  last_mutation_audit_id: z.string().nullable().optional(),
  last_mutation_audit_status: z.enum(["blocked", "applied", "failed"]).nullable().optional(),
  last_mutation_audit_actor: z.string().nullable().optional(),
  last_mutation_audit_at: z.string().nullable().optional(),
  last_mutation_audit_summary: z.string().nullable().optional(),
  last_mutation_attempted: z.boolean().nullable().optional(),
  last_mutation_adapter: z.string().nullable().optional(),
  last_mutation_audit_event_id: z.string().nullable().optional(),
  last_mutation_blockers: z.array(z.string()).default([])
});

export const ActionObjectSchema = z.object({
  id: z.string(),
  title: z.string(),
  domain: z.string(),
  connector: z.string(),
  mode: z.enum(["suggest", "prepare", "apply"]),
  risk: z.enum(["low", "medium", "high", "critical"]),
  status: z.string(),
  evidence_ids: z.array(z.string()).min(1),
  metrics: z.array(MetricFactSchema),
  human_diagnosis: z.string(),
  recommended_reason: z.string(),
  validation_status: z.string(),
  review_gate: ActionReviewGateSchema.optional().default({}),
  payload: z.record(z.unknown()),
  audit_events: z.array(AuditEventSchema)
});

export const ActionValidationResultSchema = z.object({
  action_id: z.string(),
  valid: z.boolean(),
  status: z.enum(["valid", "invalid"]),
  errors: z.array(z.string()),
  warnings: z.array(z.string()),
  checked_at: z.string()
});

export const ActionMutationAuditRecordSchema = z.object({
  id: z.string(),
  action_id: z.string(),
  connector: z.string(),
  action_type: z.string().nullable().optional(),
  status: z.enum(["blocked", "applied", "failed"]),
  mutation_attempted: z.boolean(),
  mutation_adapter: z.string().nullable().optional(),
  actor: z.string(),
  created_at: z.string(),
  audit_event_id: z.string(),
  evidence_ids: z.array(z.string()),
  blockers: z.array(z.string()),
  summary: z.string(),
  redacted: z.boolean()
});

export const ActionApplyResultSchema = z.object({
  action_id: z.string(),
  applied: z.boolean(),
  status: z.enum(["applied", "blocked", "failed"]),
  audit_event: AuditEventSchema,
  mutation_audit: ActionMutationAuditRecordSchema,
  errors: z.array(z.string())
});

export const ActionPreviewRequestSchema = z.object({
  requested_by: z.string().min(1).nullable().optional(),
  max_items: z.number().int().min(1).max(50).optional()
});

export const ActionPreviewResultSchema = z.object({
  action_id: z.string(),
  status: z.enum(["preview_ready", "blocked"]),
  dry_run: z.boolean(),
  mutation_allowed: z.boolean(),
  preview_contract: z.string().nullable().optional(),
  preview_items: z.array(z.record(z.unknown())),
  preview_items_total: z.number(),
  omitted_items: z.number(),
  blockers: z.array(z.string()),
  audit_event: AuditEventSchema,
  review_gate: ActionReviewGateSchema
});

export const ActionReviewResultSchema = z.object({
  action_id: z.string(),
  status: z.enum(["recorded"]),
  audit_event: AuditEventSchema,
  review_gate: ActionReviewGateSchema
});

export const ActionConfirmRequestSchema = z.object({
  confirmed_by: z.string().min(1),
  notes: z.string().min(1).max(2000),
  preview_acknowledged: z.boolean().default(false)
});

export const ActionConfirmResultSchema = z.object({
  action_id: z.string(),
  confirmed: z.boolean(),
  status: z.enum(["confirmed", "blocked"]),
  blockers: z.array(z.string()),
  audit_event: AuditEventSchema,
  review_gate: ActionReviewGateSchema
});

export const ActionImpactCheckRequestSchema = z.object({
  checked_by: z.string().min(1),
  notes: z.string().min(1).max(2000),
  pre_window_days: z.number().int().min(1).max(90).optional(),
  post_window_days: z.number().int().min(1).max(90).optional()
});

export const ActionImpactCheckResultSchema = z.object({
  action_id: z.string(),
  status: z.enum(["checked", "blocked"]),
  pre_window_days: z.number(),
  post_window_days: z.number(),
  metric_fact_count: z.number(),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  blockers: z.array(z.string()),
  audit_event: AuditEventSchema,
  review_gate: ActionReviewGateSchema
});

export const ActionApplyRequestSchema = z.object({
  confirm: z.boolean(),
  confirmed_by: z.string().min(1)
});

export const ConnectorSummarySchema = z.object({
  total: z.number(),
  configured: z.number(),
  missing_credentials: z.number()
});

export const MarketingBriefItemSchema = z.object({
  id: z.string(),
  title: z.string(),
  kind: z.enum(["metric", "blocker", "action", "recommendation"]),
  priority: z.number(),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  metric_facts: z.array(MetricFactSchema),
  action_ids: z.array(z.string()),
  summary: z.string(),
  next_step: z.string(),
  risk: z.string(),
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
  priority: z.number(),
  risk: z.enum(["low", "medium", "high", "critical"]),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  metric_facts: z.array(MetricFactSchema),
  dimensions: z.record(z.string()).optional().default({}),
  diagnosis: z.string(),
  next_step: z.string(),
  blocked_claims: z.array(z.string()),
  action_ids: z.array(z.string())
});

export const TacticalQueueResponseSchema = z.object({
  generated_at: z.string().nullable().optional(),
  language: z.literal("pl-PL"),
  strict_instruction: z.string(),
  items: z.array(TacticalQueueItemSchema),
  evidence_ids: z.array(z.string()),
  action_ids: z.array(z.string())
});

export const AdsDiagnosticSectionSchema = z.object({
  id: z.string(),
  title: z.string(),
  status: z.enum(["ready", "blocked", "missing"]),
  summary: z.string(),
  diagnosis: z.string(),
  next_step: z.string(),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  metric_facts: z.array(MetricFactSchema),
  action_ids: z.array(z.string()),
  knowledge_card_ids: z.array(z.string()).optional().default([]),
  expert_rule_ids: z.array(z.string()).optional().default([]),
  blocked_claims: z.array(z.string()),
  risk: z.enum(["low", "medium", "high", "critical"])
});

export const AdsBlockedHandoffSchema = z.object({
  id: z.string(),
  status: z.enum(["ready", "blocked"]),
  title: z.string(),
  summary: z.string(),
  marketer_message: z.string(),
  repair_steps: z.array(z.string()),
  allowed_demo_claims: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  action_ids: z.array(z.string())
});

export const AdsCampaignMetricRowSchema = z.object({
  campaign_id: z.string().nullable().optional(),
  campaign_name: z.string(),
  campaign_status: z.string().nullable().optional(),
  advertising_channel_type: z.string().nullable().optional(),
  clicks: z.number().nullable().optional(),
  impressions: z.number().nullable().optional(),
  cost_micros: z.number().nullable().optional(),
  conversions: z.number().nullable().optional(),
  conversion_value: z.number().nullable().optional(),
  evidence_ids: z.array(z.string()),
  metric_facts: z.array(MetricFactSchema),
  missing_metrics: z.array(z.string()),
  blocked_claims: z.array(z.string()),
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
  human_review_gates: z.array(z.string()).default([])
});

export const AdsCampaignReadContractSchema = z.object({
  id: z.string(),
  status: z.enum(["ready", "blocked"]),
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
  summary: z.string(),
  allowed_uses: z.array(z.string()),
  blocked_uses: z.array(z.string()),
  missing_requirements: z.array(z.string()),
  required_validation: z.array(z.string()),
  policy_ids: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  action_ids: z.array(z.string()).optional().default([]),
  apply_allowed: z.boolean(),
  destructive: z.boolean()
});

export const AdsBusinessContextReadContractSchema = z.object({
  id: z.string(),
  status: z.enum(["ready", "blocked"]),
  title: z.string(),
  summary: z.string(),
  profit_margin: z.number().nullable().optional(),
  business_goal: z.string().nullable().optional(),
  budget_goal: z.string().nullable().optional(),
  target_roas: z.number().nullable().optional(),
  target_cpa_micros: z.number().nullable().optional(),
  configured_sources: z.array(z.string()),
  business_policy_ids: z.array(z.string()).optional().default([]),
  operator_review_gates: z.array(z.string()).optional().default([]),
  target_interpretation: AdsBusinessTargetInterpretationSchema,
  allowed_metrics: z.array(z.string()),
  missing_read_contracts: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  metric_tiles: z.record(z.union([z.string(), z.number()])),
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
  blocked_claims: z.array(z.string())
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
  reason: z.string(),
  max_allowed_delta_percent: z.number(),
  current_budget_amount_micros: z.number().nullable().optional(),
  proposed_budget_amount_micros: z.number().nullable().optional(),
  proposed_delta_percent: z.number().nullable().optional(),
  missing_requirements: z.array(z.string()),
  required_validation: z.array(z.string()),
  blocked_claims: z.array(z.string()),
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
  current_budget_amount_micros: z.number().nullable().optional(),
  proposed_budget_amount_micros: z.number().nullable().optional(),
  proposed_budget_delta_micros: z.number().nullable().optional(),
  reason: z.string(),
  evidence_ids: z.array(z.string()),
  source_metric_names: z.array(z.string()),
  required_validation: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  safety_review: AdsBudgetApplySafetyReviewSchema,
  api_mutation_ready: z.boolean(),
  apply_allowed: z.boolean(),
  destructive: z.boolean()
});

export const AdsBudgetPacingRowSchema = z.object({
  campaign_id: z.string().nullable().optional(),
  campaign_name: z.string(),
  campaign_status: z.string().nullable().optional(),
  advertising_channel_type: z.string().nullable().optional(),
  budget_id: z.string().nullable().optional(),
  budget_name: z.string().nullable().optional(),
  budget_period: z.string().nullable().optional(),
  budget_status: z.string().nullable().optional(),
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
  missing_metrics: z.array(z.string()),
  blocked_claims: z.array(z.string())
});

export const AdsBudgetPacingReadContractSchema = z.object({
  id: z.string(),
  status: z.enum(["ready", "blocked"]),
  title: z.string(),
  summary: z.string(),
  allowed_metrics: z.array(z.string()),
  missing_read_contracts: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  budget_rows: z.array(AdsBudgetPacingRowSchema),
  payload_preview: z.array(AdsBudgetApplyPreviewSchema),
  action_ids: z.array(z.string()),
  next_step: z.string()
});

export const AdsRecommendationApplyPreviewSchema = z.object({
  id: z.string(),
  recommendation_id: z.string().nullable().optional(),
  recommendation_resource_name: z.string().nullable().optional(),
  recommendation_type: z.string(),
  campaign_id: z.string().nullable().optional(),
  campaign_budget_id: z.string().nullable().optional(),
  operation_type: z.literal("ApplyRecommendationOperation"),
  reason: z.string(),
  evidence_ids: z.array(z.string()),
  source_metric_names: z.array(z.string()),
  required_validation: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  api_mutation_ready: z.boolean(),
  apply_allowed: z.boolean(),
  destructive: z.boolean()
});

export const AdsRecommendationRowSchema = z.object({
  recommendation_id: z.string().nullable().optional(),
  recommendation_resource_name: z.string().nullable().optional(),
  recommendation_type: z.string(),
  review_priority: z
    .enum(["pilne", "wysokie", "normalne", "niski sygnał"])
    .default("normalne"),
  review_score: z.number().min(0).max(100).default(0),
  review_reason: z.string(),
  human_review_gates: z.array(z.string()).default([]),
  dismissed: z.boolean(),
  campaign_id: z.string().nullable().optional(),
  campaign_budget_id: z.string().nullable().optional(),
  campaign_count: z.number().nullable().optional(),
  impact_available: z.boolean(),
  base_clicks: z.number().nullable().optional(),
  potential_clicks: z.number().nullable().optional(),
  delta_clicks: z.number().nullable().optional(),
  base_impressions: z.number().nullable().optional(),
  potential_impressions: z.number().nullable().optional(),
  delta_impressions: z.number().nullable().optional(),
  base_cost_micros: z.number().nullable().optional(),
  potential_cost_micros: z.number().nullable().optional(),
  delta_cost_micros: z.number().nullable().optional(),
  base_conversions: z.number().nullable().optional(),
  potential_conversions: z.number().nullable().optional(),
  delta_conversions: z.number().nullable().optional(),
  base_conversion_value: z.number().nullable().optional(),
  potential_conversion_value: z.number().nullable().optional(),
  delta_conversion_value: z.number().nullable().optional(),
  evidence_ids: z.array(z.string()),
  metric_facts: z.array(MetricFactSchema),
  payload_preview: AdsRecommendationApplyPreviewSchema.nullable().optional(),
  missing_metrics: z.array(z.string()),
  blocked_claims: z.array(z.string())
});

export const AdsRecommendationsReadContractSchema = z.object({
  id: z.string(),
  status: z.enum(["ready", "blocked"]),
  title: z.string(),
  summary: z.string(),
  allowed_metrics: z.array(z.string()),
  missing_read_contracts: z.array(z.string()),
  operator_review_gates: z.array(z.string()).optional().default([]),
  blocked_claims: z.array(z.string()),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  recommendation_rows: z.array(AdsRecommendationRowSchema),
  payload_preview: z.array(AdsRecommendationApplyPreviewSchema),
  action_ids: z.array(z.string()),
  next_step: z.string()
});

export const AdsImpressionShareRowSchema = z.object({
  campaign_id: z.string().nullable().optional(),
  campaign_name: z.string(),
  campaign_status: z.string().nullable().optional(),
  advertising_channel_type: z.string().nullable().optional(),
  search_impression_share: z.number().nullable().optional(),
  search_budget_lost_impression_share: z.number().nullable().optional(),
  search_rank_lost_impression_share: z.number().nullable().optional(),
  evidence_ids: z.array(z.string()),
  metric_facts: z.array(MetricFactSchema),
  missing_metrics: z.array(z.string()),
  blocked_claims: z.array(z.string())
});

export const AdsImpressionShareReadContractSchema = z.object({
  id: z.string(),
  status: z.enum(["ready", "blocked"]),
  title: z.string(),
  summary: z.string(),
  allowed_metrics: z.array(z.string()),
  missing_read_contracts: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  impression_share_rows: z.array(AdsImpressionShareRowSchema),
  next_step: z.string()
});

export const AdsChangeHistoryRowSchema = z.object({
  change_event_id: z.string().nullable().optional(),
  change_date_time: z.string().nullable().optional(),
  change_resource_id: z.string().nullable().optional(),
  change_resource_type: z.string().nullable().optional(),
  resource_change_operation: z.string().nullable().optional(),
  client_type: z.string().nullable().optional(),
  campaign_id: z.string().nullable().optional(),
  changed_field_count: z.number().nullable().optional(),
  changed_fields: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  metric_facts: z.array(MetricFactSchema),
  missing_metrics: z.array(z.string()),
  blocked_claims: z.array(z.string())
});

export const AdsChangeHistoryReadContractSchema = z.object({
  id: z.string(),
  status: z.enum(["ready", "blocked"]),
  title: z.string(),
  summary: z.string(),
  allowed_metrics: z.array(z.string()),
  missing_read_contracts: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  change_history_rows: z.array(AdsChangeHistoryRowSchema),
  action_ids: z.array(z.string()).optional().default([]),
  next_step: z.string()
});

export const AdsSearchTermMetricRowSchema = z.object({
  search_term: z.string(),
  campaign_id: z.string().nullable().optional(),
  campaign_name: z.string().nullable().optional(),
  ad_group_id: z.string().nullable().optional(),
  ad_group_name: z.string().nullable().optional(),
  search_term_status: z.string().nullable().optional(),
  clicks: z.number().nullable().optional(),
  impressions: z.number().nullable().optional(),
  cost_micros: z.number().nullable().optional(),
  conversions: z.number().nullable().optional(),
  conversion_value: z.number().nullable().optional(),
  evidence_ids: z.array(z.string()),
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
  operator_review_gates: z.array(z.string()).optional().default([]),
  blocked_claims: z.array(z.string()),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  search_term_rows: z.array(AdsSearchTermMetricRowSchema),
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
  blocked_claims: z.array(z.string()),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  ngram_rows: z.array(AdsSearchTermNgramRowSchema),
  next_step: z.string()
});

export const AdsSearchTermSafetyRowSchema = z.object({
  search_term: z.string(),
  campaign_id: z.string().nullable().optional(),
  campaign_name: z.string().nullable().optional(),
  ad_group_id: z.string().nullable().optional(),
  ad_group_name: z.string().nullable().optional(),
  search_term_status: z.string().nullable().optional(),
  clicks_90d: z.number().nullable().optional(),
  impressions_90d: z.number().nullable().optional(),
  cost_micros_90d: z.number().nullable().optional(),
  conversions_90d: z.number().nullable().optional(),
  conversion_value_90d: z.number().nullable().optional(),
  evidence_ids: z.array(z.string()),
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
  blocked_claims: z.array(z.string()),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  safety_rows: z.array(AdsSearchTermSafetyRowSchema),
  next_step: z.string()
});

export const AdsKeywordMatchContextRowSchema = z.object({
  keyword_text: z.string(),
  match_type: z.string(),
  criterion_id: z.string().nullable().optional(),
  criterion_status: z.string().nullable().optional(),
  negative: z.boolean().nullable().optional(),
  campaign_id: z.string().nullable().optional(),
  campaign_name: z.string().nullable().optional(),
  ad_group_id: z.string().nullable().optional(),
  ad_group_name: z.string().nullable().optional(),
  evidence_ids: z.array(z.string()),
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
  blocked_claims: z.array(z.string()),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  context_rows: z.array(AdsKeywordMatchContextRowSchema),
  next_step: z.string()
});

export const AdsCustomSegmentTargetingPreviewSchema = z.object({
  id: z.string(),
  custom_segment_preview_id: z.string(),
  target_scope: z.literal("campaign_context_review"),
  campaign_id: z.string().nullable().optional(),
  campaign_name: z.string().nullable().optional(),
  operation_type: z.literal("custom_segment_targeting_review"),
  reason: z.string(),
  required_validation: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  api_mutation_ready: z.boolean(),
  apply_allowed: z.boolean(),
  destructive: z.boolean()
});

export const AdsCustomSegmentPayloadPreviewSchema = z.object({
  id: z.string(),
  custom_segment_name: z.string(),
  member_type: z.literal("KEYWORD"),
  source_terms: z.array(z.string()),
  campaign_id: z.string().nullable().optional(),
  campaign_name: z.string().nullable().optional(),
  reason: z.string(),
  evidence_ids: z.array(z.string()),
  source_metric_names: z.array(z.string()),
  required_validation: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  targeting_preview: z.array(AdsCustomSegmentTargetingPreviewSchema).optional().default([]),
  api_mutation_ready: z.boolean(),
  apply_allowed: z.boolean(),
  destructive: z.boolean()
});

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
  title: z.string(),
  summary: z.string(),
  allowed_metrics: z.array(z.string()),
  missing_read_contracts: z.array(z.string()),
  operator_review_gates: z.array(z.string()).optional().default([]),
  blocked_claims: z.array(z.string()),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  idea_rows: z.array(AdsKeywordPlannerIdeaRowSchema),
  next_step: z.string()
});

export const AdsCustomSegmentCandidateSchema = z.object({
  id: z.string(),
  name: z.string(),
  intent: z.string(),
  review_priority: z
    .enum(["pilne", "wysokie", "normalne", "niski sygnał"])
    .default("normalne"),
  review_score: z.number().min(0).max(100).default(0),
  review_reason: z.string(),
  human_review_gates: z.array(z.string()).default([]),
  source_terms: z.array(z.string()),
  rejected_terms: z.array(z.string()),
  rejection_reasons: z.array(z.string()),
  source_quality: z
    .object({
      total_terms: z.number().int().nonnegative().default(0),
      accepted_terms: z.number().int().nonnegative().default(0),
      rejected_terms: z.number().int().nonnegative().default(0),
      missing_metric_terms: z.number().int().nonnegative().default(0),
      rejection_reasons: z.record(z.string(), z.number().int().nonnegative()).default({})
    })
    .default({
      total_terms: 0,
      accepted_terms: 0,
      rejected_terms: 0,
      missing_metric_terms: 0,
      rejection_reasons: {}
    }),
  search_term_rows: z.array(AdsSearchTermMetricRowSchema),
  keyword_planner_ideas: z.array(AdsKeywordPlannerIdeaRowSchema).optional().default([]),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  metric_facts: z.array(MetricFactSchema),
  confidence: z.enum(["low", "medium", "high"]),
  validation_status: z.enum(["pending_validation", "blocked"]),
  payload_preview: AdsCustomSegmentPayloadPreviewSchema.nullable().optional(),
  blocked_claims: z.array(z.string()),
  next_step: z.string()
});

export const AdsCustomSegmentsReadContractSchema = z.object({
  id: z.string(),
  status: z.enum(["ready", "blocked"]),
  title: z.string(),
  summary: z.string(),
  candidates: z.array(AdsCustomSegmentCandidateSchema),
  payload_preview: z.array(AdsCustomSegmentPayloadPreviewSchema),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  missing_read_contracts: z.array(z.string()),
  operator_review_gates: z.array(z.string()).optional().default([]),
  blocked_claims: z.array(z.string()),
  action_ids: z.array(z.string()),
  next_step: z.string()
});

export const AdsNegativeKeywordPayloadPreviewSchema = z.object({
  id: z.string(),
  search_term: z.string(),
  negative_keyword_text: z.string(),
  match_type: z.literal("EXACT"),
  level: z.enum(["ad_group", "campaign_review_required"]),
  campaign_id: z.string().nullable().optional(),
  campaign_name: z.string().nullable().optional(),
  ad_group_id: z.string().nullable().optional(),
  ad_group_name: z.string().nullable().optional(),
  reason: z.string(),
  evidence_ids: z.array(z.string()),
  source_metric_names: z.array(z.string()),
  required_validation: z.array(z.string()),
  blocked_claims: z.array(z.string()),
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
  campaign_id: z.string().nullable().optional(),
  campaign_name: z.string().nullable().optional(),
  ad_group_id: z.string().nullable().optional(),
  ad_group_name: z.string().nullable().optional(),
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
  required_checks: z.array(z.string()),
  safety_status: z.enum(["needs_90_day_review", "read_ready_needs_human_review", "blocked"]),
  validation_status: z.enum(["pending_validation", "blocked"]),
  blocked_claims: z.array(z.string()),
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
  blocked_claims: z.array(z.string()),
  action_ids: z.array(z.string()),
  next_step: z.string()
});

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
    "review_search_term_safety",
    "review_search_terms",
    "review_search_term_ngrams",
    "review_negative_keyword_safety",
    "prepare_custom_segments",
    "block_write_actions",
    "fix_ads_access"
  ]),
  status: z.enum(["ready", "blocked"]),
  title: z.string(),
  summary: z.string(),
  rationale: z.string(),
  next_step: z.string(),
  priority: z.number().default(50),
  metric_tiles: z.record(z.union([z.string(), z.number()])).default({}),
  allowed_metrics: z.array(z.string()),
  missing_read_contracts: z.array(z.string()),
  operator_review_gates: z.array(z.string()).optional().default([]),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  metric_facts: z.array(MetricFactSchema),
  campaign_rows: z.array(AdsCampaignMetricRowSchema),
  derived_kpi_rows: z.array(AdsDerivedKpiRowSchema),
  budget_rows: z.array(AdsBudgetPacingRowSchema),
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
  negative_keyword_candidates: z.array(AdsNegativeKeywordCandidateSchema),
  negative_keyword_payload_preview: z.array(AdsNegativeKeywordPayloadPreviewSchema),
  action_ids: z.array(z.string()),
  knowledge_card_ids: z.array(z.string()).optional().default([]),
  expert_rule_ids: z.array(z.string()).optional().default([]),
  blocked_claims: z.array(z.string()),
  risk: z.enum(["low", "medium", "high", "critical"])
});

export const AdsDiagnosticsResponseSchema = z.object({
  generated_at: z.string().nullable().optional(),
  language: z.literal("pl-PL"),
  strict_instruction: z.string(),
  connector: ConnectorStatusSchema,
  latest_refresh: ConnectorRefreshRunSchema.nullable().optional(),
  live_data_available: z.boolean(),
  campaign_read_contract: AdsCampaignReadContractSchema,
  account_currency_read_contract: AdsAccountCurrencyReadContractSchema,
  business_context_read_contract: AdsBusinessContextReadContractSchema,
  derived_kpi_read_contract: AdsDerivedKpiReadContractSchema,
  budget_pacing_read_contract: AdsBudgetPacingReadContractSchema,
  recommendations_read_contract: AdsRecommendationsReadContractSchema,
  impression_share_read_contract: AdsImpressionShareReadContractSchema,
  change_history_read_contract: AdsChangeHistoryReadContractSchema,
  search_terms_read_contract: AdsSearchTermsReadContractSchema,
  search_term_ngram_read_contract: AdsSearchTermNgramReadContractSchema,
  search_term_safety_read_contract: AdsSearchTermSafetyReadContractSchema,
  keyword_match_context_read_contract: AdsKeywordMatchContextReadContractSchema,
  keyword_planner_read_contract: AdsKeywordPlannerReadContractSchema,
  custom_segments_read_contract: AdsCustomSegmentsReadContractSchema,
  negative_keywords_read_contract: AdsNegativeKeywordsReadContractSchema,
  decision_queue: z.array(AdsDecisionItemSchema),
  sections: z.array(AdsDiagnosticSectionSchema),
  blocked_handoff: AdsBlockedHandoffSchema.nullable().optional(),
  evidence_ids: z.array(z.string()),
  action_ids: z.array(z.string()),
  blocker_count: z.number()
});

export const MerchantDiagnosticSectionSchema = z.object({
  id: z.string(),
  title: z.string(),
  status: z.enum(["ready", "blocked", "missing"]),
  summary: z.string(),
  diagnosis: z.string(),
  next_step: z.string(),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  metric_facts: z.array(MetricFactSchema),
  tactical_items: z.array(TacticalQueueItemSchema),
  action_ids: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  risk: z.enum(["low", "medium", "high", "critical"])
});

export const MerchantIssueClusterSchema = z.object({
  id: z.string(),
  issue_type: z.string(),
  severity: z.string(),
  resolution: z.string().nullable().optional(),
  affected_attribute: z.string().nullable().optional(),
  country: z.string().nullable().optional(),
  reporting_context: z.string().nullable().optional(),
  product_count: z.number(),
  sample_product_ids: z.array(z.string()),
  sample_titles: z.array(z.string()),
  sample_unavailable_reason: z.string().nullable().optional(),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  action_id: z.string().nullable().optional(),
  risk: z.enum(["low", "medium", "high", "critical"]),
  next_step: z.string()
});

export const MerchantDecisionItemSchema = z.object({
  id: z.string(),
  decision_type: z.enum([
    "review_issue_cluster",
    "review_feed_status",
    "block_until_vendor_read"
  ]),
  status: z.enum(["ready", "blocked", "missing"]),
  title: z.string(),
  summary: z.string().nullable().optional(),
  cluster_id: z.string().nullable().optional(),
  issue_type: z.string().nullable().optional(),
  severity: z.string().nullable().optional(),
  resolution: z.string().nullable().optional(),
  affected_attribute: z.string().nullable().optional(),
  country: z.string().nullable().optional(),
  reporting_context: z.string().nullable().optional(),
  product_count: z.number().nullable().optional(),
  issue_count: z.number().nullable().optional(),
  priority: z.number(),
  metric_tiles: z.record(z.union([z.string(), z.number()])).default({}),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  metric_facts: z.array(MetricFactSchema),
  action_ids: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  rationale: z.string(),
  next_step: z.string(),
  risk: z.enum(["low", "medium", "high", "critical"])
});

export const MerchantDiagnosticsResponseSchema = z.object({
  generated_at: z.string().nullable().optional(),
  language: z.literal("pl-PL"),
  strict_instruction: z.string(),
  connector: ConnectorStatusSchema,
  latest_refresh: ConnectorRefreshRunSchema.nullable().optional(),
  live_data_available: z.boolean(),
  product_count: z.number().nullable().optional(),
  issue_count: z.number().nullable().optional(),
  issue_clusters: z.array(MerchantIssueClusterSchema),
  decision_queue: z.array(MerchantDecisionItemSchema),
  sections: z.array(MerchantDiagnosticSectionSchema),
  evidence_ids: z.array(z.string()),
  action_ids: z.array(z.string()),
  blocker_count: z.number()
});

export const ContentDiagnosticSectionSchema = z.object({
  id: z.string(),
  title: z.string(),
  status: z.enum(["ready", "blocked", "missing"]),
  summary: z.string(),
  diagnosis: z.string(),
  next_step: z.string(),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  metric_facts: z.array(MetricFactSchema),
  tactical_items: z.array(TacticalQueueItemSchema),
  action_ids: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  risk: z.enum(["low", "medium", "high", "critical"])
});

export const ContentDecisionItemSchema = z.object({
  id: z.string(),
  decision_type: z.enum([
    "refresh_or_merge",
    "merge_create_after_inventory_check",
    "inventory_check_before_create",
    "block_as_tracking_not_content",
    "review_ahrefs_gap_records"
  ]),
  status: z.enum(["ready", "blocked"]),
  title: z.string(),
  summary: z.string().nullable().optional(),
  priority: z.number(),
  metric_tiles: z.record(z.union([z.string(), z.number()])),
  page: z.string().nullable().optional(),
  normalized_page_path: z.string().nullable().optional(),
  queries: z.array(z.string()),
  query_count: z.number(),
  primary_query: z.string().nullable().optional(),
  total_clicks: z.number().nullable().optional(),
  total_impressions: z.number().nullable().optional(),
  aggregate_ctr: z.number().nullable().optional(),
  best_average_position: z.number().nullable().optional(),
  wordpress_match: z.string().nullable().optional(),
  wordpress_match_confidence: z.string().nullable().optional(),
  wordpress_content_url: z.string().nullable().optional(),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  metric_facts: z.array(MetricFactSchema),
  ahrefs_candidate_rows: z
    .array(
      z.object({
        id: z.string(),
        topic: z.string(),
        gap_type: z.string(),
        relevance_status: z.enum(["relevant", "review", "off_topic"]),
        relevance_score: z.number(),
        business_relevance_reasons: z.array(z.string()).default([]),
        gsc_demand: z.enum(["present", "missing"]),
        wordpress_inventory_match: z.enum(["present", "missing"]),
        gsc_overlap_terms: z.array(z.string()).default([]),
        wordpress_overlap_urls: z.array(z.string()).default([]),
        keyword: z.string().nullable().optional(),
        competitor_domain: z.string().nullable().optional(),
        source_url: z.string().nullable().optional(),
        target_url: z.string().nullable().optional(),
        metric_name: z.string(),
        metric_value: z.union([z.string(), z.number()]),
        evidence_ids: z.array(z.string()),
        next_step: z.string()
      })
    )
    .default([]),
  action_ids: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  rationale: z.string(),
  next_step: z.string(),
  risk: z.enum(["low", "medium", "high", "critical"])
});

export const ContentDiagnosticsResponseSchema = z.object({
  generated_at: z.string().nullable().optional(),
  language: z.literal("pl-PL"),
  strict_instruction: z.string(),
  connectors: z.array(ConnectorStatusSchema),
  latest_refreshes: z.array(ConnectorRefreshRunSchema),
  live_data_available: z.boolean(),
  query_page_count: z.number(),
  matched_inventory_count: z.number(),
  decision_queue: z.array(ContentDecisionItemSchema),
  sections: z.array(ContentDiagnosticSectionSchema),
  evidence_ids: z.array(z.string()),
  action_ids: z.array(z.string()),
  blocker_count: z.number()
});

export const Ga4DiagnosticSectionSchema = z.object({
  id: z.string(),
  title: z.string(),
  status: z.enum(["ready", "blocked", "missing"]),
  summary: z.string(),
  diagnosis: z.string(),
  next_step: z.string(),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  metric_facts: z.array(MetricFactSchema),
  tactical_items: z.array(TacticalQueueItemSchema),
  action_ids: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  risk: z.enum(["low", "medium", "high", "critical"])
});

export const Ga4DecisionItemSchema = z.object({
  id: z.string(),
  decision_type: z.enum([
    "fix_measurement",
    "review_traffic_quality",
    "review_landing_mapping"
  ]),
  title: z.string(),
  status: z.enum(["ready", "blocked"]),
  priority: z.number(),
  metric_tiles: z.record(z.union([z.string(), z.number()])),
  landing_page: z.string().nullable().optional(),
  source_medium: z.string().nullable().optional(),
  campaign_name: z.string().nullable().optional(),
  wordpress_match: z.string().nullable().optional(),
  wordpress_match_confidence: z.string().nullable().optional(),
  wordpress_content_url: z.string().nullable().optional(),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  metric_facts: z.array(MetricFactSchema),
  action_ids: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  rationale: z.string(),
  next_step: z.string(),
  risk: z.enum(["low", "medium", "high", "critical"])
});

export const Ga4DiagnosticsResponseSchema = z.object({
  generated_at: z.string().nullable().optional(),
  language: z.literal("pl-PL"),
  strict_instruction: z.string(),
  connector: ConnectorStatusSchema,
  latest_refresh: ConnectorRefreshRunSchema.nullable().optional(),
  live_data_available: z.boolean(),
  landing_group_count: z.number(),
  low_engagement_count: z.number(),
  wordpress_match_count: z.number(),
  decision_queue: z.array(Ga4DecisionItemSchema),
  sections: z.array(Ga4DiagnosticSectionSchema),
  evidence_ids: z.array(z.string()),
  action_ids: z.array(z.string()),
  blocker_count: z.number()
});

export const LocaloAccessProbeSchema = z.object({
  status: z.enum(["access_ready", "access_blocked", "unknown"]),
  source_run_id: z.string().nullable().optional(),
  mcp_initialize_status: z.number().nullable().optional(),
  authorization_code_supported: z.boolean().nullable().optional(),
  pkce_s256_supported: z.boolean().nullable().optional(),
  access_token_present: z.boolean().nullable().optional(),
  evidence_ids: z.array(z.string()),
  summary: z.string()
});

export const LocaloDiagnosticSectionSchema = z.object({
  id: z.string(),
  title: z.string(),
  status: z.enum(["ready", "blocked", "missing"]),
  summary: z.string(),
  diagnosis: z.string(),
  next_step: z.string(),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  metric_facts: z.array(MetricFactSchema),
  action_ids: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  risk: z.enum(["low", "medium", "high", "critical"])
});

export const LocaloDecisionItemSchema = z.object({
  id: z.string(),
  decision_type: z.enum([
    "access_ready_wait_for_visibility_facts",
    "fix_access",
    "review_local_visibility",
    "block_visibility_claims"
  ]),
  status: z.enum(["ready", "blocked"]),
  title: z.string(),
  summary: z.string(),
  rationale: z.string(),
  next_step: z.string(),
  access_status: z.enum(["access_ready", "access_blocked", "unknown"]),
  priority: z.number(),
  metric_tiles: z.record(z.union([z.string(), z.number()])).default({}),
  allowed_evidence: z.array(z.string()),
  missing_read_contracts: z.array(z.string()),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  metric_facts: z.array(MetricFactSchema),
  action_ids: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  risk: z.enum(["low", "medium", "high", "critical"])
});

export const LocaloDiagnosticsResponseSchema = z.object({
  generated_at: z.string().nullable().optional(),
  language: z.literal("pl-PL"),
  strict_instruction: z.string(),
  connector: ConnectorStatusSchema,
  latest_refresh: ConnectorRefreshRunSchema.nullable().optional(),
  access_probe: LocaloAccessProbeSchema,
  live_data_available: z.boolean(),
  visibility_fact_count: z.number(),
  decision_queue: z.array(LocaloDecisionItemSchema),
  sections: z.array(LocaloDiagnosticSectionSchema),
  evidence_ids: z.array(z.string()),
  action_ids: z.array(z.string()),
  blocker_count: z.number()
});

export const AhrefsDiagnosticSectionSchema = z.object({
  id: z.string(),
  title: z.string(),
  status: z.enum(["ready", "blocked", "missing"]),
  summary: z.string(),
  diagnosis: z.string(),
  next_step: z.string(),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  metric_facts: z.array(MetricFactSchema),
  action_ids: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  risk: z.enum(["low", "medium", "high", "critical"])
});

export const AhrefsDecisionItemSchema = z.object({
  id: z.string(),
  decision_type: z.enum([
    "review_authority_context",
    "review_gap_records",
    "run_authority_read",
    "block_gap_claims"
  ]),
  status: z.enum(["ready", "blocked"]),
  title: z.string(),
  summary: z.string(),
  rationale: z.string(),
  next_step: z.string(),
  priority: z.number(),
  metric_tiles: z.record(z.union([z.string(), z.number()])).default({}),
  allowed_evidence: z.array(z.string()),
  missing_read_contracts: z.array(z.string()),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  metric_facts: z.array(MetricFactSchema),
  action_ids: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  risk: z.enum(["low", "medium", "high", "critical"])
});

export const AhrefsGapRecordSchema = z.object({
  id: z.string(),
  gap_type: z.enum([
    "competitor_page",
    "content_gap",
    "backlink_gap",
    "organic_keyword_gap",
    "top_page_gap"
  ]),
  title: z.string(),
  summary: z.string(),
  source_url: z.string().nullable().optional(),
  target_url: z.string().nullable().optional(),
  competitor_domain: z.string().nullable().optional(),
  keyword: z.string().nullable().optional(),
  metric_facts: z.array(MetricFactSchema),
  evidence_ids: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  next_step: z.string(),
  risk: z.enum(["low", "medium", "high", "critical"])
});

export const AhrefsGapReadContractSchema = z.object({
  id: z.literal("ahrefs_gap_read_contract"),
  status: z.enum(["ready", "blocked"]),
  title: z.string(),
  summary: z.string(),
  available_read_contracts: z.array(z.string()),
  missing_read_contracts: z.array(z.string()),
  allowed_evidence: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  operator_review_gates: z.array(z.string()),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  gap_records: z.array(AhrefsGapRecordSchema),
  next_step: z.string(),
  risk: z.enum(["low", "medium", "high", "critical"])
});

export const AhrefsDiagnosticsResponseSchema = z.object({
  generated_at: z.string().nullable().optional(),
  language: z.literal("pl-PL"),
  strict_instruction: z.string(),
  connector: ConnectorStatusSchema,
  latest_refresh: ConnectorRefreshRunSchema.nullable().optional(),
  live_data_available: z.boolean(),
  authority_fact_count: z.number(),
  gap_fact_count: z.number(),
  gap_read_contract: AhrefsGapReadContractSchema,
  decision_queue: z.array(AhrefsDecisionItemSchema),
  sections: z.array(AhrefsDiagnosticSectionSchema),
  evidence_ids: z.array(z.string()),
  action_ids: z.array(z.string()),
  blocker_count: z.number()
});

export const ExpertRuleSchema = z.object({
  id: z.string(),
  name: z.string(),
  domain: z.string(),
  version: z.number(),
  source_anchor: z.string(),
  source_path: z.string(),
  when_to_use: z.string().nullable().optional(),
  required_inputs: z.array(z.string()),
  diagnostic_logic: z.array(z.string()),
  recommended_actions: z.array(z.string()),
  risk_notes: z.string().nullable().optional(),
  output_contract: z.string(),
  capabilities: z.array(z.string()),
  required_mapping: z.array(z.string()),
  requires_evidence: z.boolean()
});

export const ExpertRuleSummarySchema = z.object({
  id: z.string(),
  name: z.string(),
  domain: z.string(),
  source_anchor: z.string(),
  required_inputs: z.array(z.string()),
  recommended_actions: z.array(z.string()),
  output_contract: z.string(),
  requires_evidence: z.boolean()
});

export const ExpertCapabilitySchema = z.object({
  id: z.string(),
  domain: z.string(),
  source_rule_id: z.string(),
  required_mapping: z.array(z.string()),
  output_contract: z.string(),
  requires_evidence: z.boolean()
});

export const KnowledgeCardSchema = z.object({
  id: z.string(),
  card_type: z.string(),
  title: z.string(),
  summary: z.string(),
  source_type: z.string(),
  source_id: z.string(),
  source_url_or_path: z.string(),
  extracted_at: z.string(),
  confidence: z.number(),
  last_seen_at: z.string(),
  source_lineage: z.array(z.string())
});

export const MarketingPlaybookSchema = z.object({
  id: z.string(),
  family: z.string(),
  title: z.string(),
  card_type: z.string(),
  source_anchors: z.array(z.string()).min(1),
  required_evidence: z.array(z.string()).min(1),
  maps_to_opportunity_types: z.array(z.string()).min(1),
  maps_to_action_types: z.array(z.string()).min(1),
  expert_rule_ids: z.array(z.string()),
  compact_playbook: z.string(),
  refusal_rules: z.array(z.string()),
  output_contract: z.string(),
  source_path: z.string()
});

export const KnowledgeCompilerResultSchema = z.object({
  status: z.enum(["completed", "failed"]),
  generated_at: z.string(),
  card_count: z.number(),
  cards: z.array(KnowledgeCardSchema)
});

export const KnowledgeDecisionBindingSchema = z.object({
  id: z.string(),
  title: z.string(),
  status: z.enum(["ready", "blocked", "planned"]),
  route: z.string(),
  skill_id: z.string().nullable().optional(),
  summary: z.string(),
  next_step: z.string(),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  action_ids: z.array(z.string()),
  metric_tiles: z.record(z.union([z.string(), z.number()])),
  knowledge_card_ids: z.array(z.string()),
  playbook_ids: z.array(z.string()),
  expert_rule_ids: z.array(z.string()),
  required_evidence: z.array(z.string()),
  missing_contracts: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  source_lineage: z.array(z.string()),
  risk: z.enum(["low", "medium", "high"])
});

export const KnowledgeOperatingMapResponseSchema = z.object({
  generated_at: z.string(),
  source_card_count: z.number(),
  playbook_count: z.number(),
  expert_rule_count: z.number(),
  binding_count: z.number(),
  bindings: z.array(KnowledgeDecisionBindingSchema)
});

export const CommandCenterBriefItemSchema = z.object({
  id: z.string(),
  title: z.string(),
  route: z.string(),
  status: z.enum(["ready", "blocked", "missing"]),
  priority: z.number(),
  summary: z.string(),
  next_step: z.string(),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  action_ids: z.array(z.string()),
  metric_tiles: z.record(z.union([z.string(), z.number()])),
  blocked_claims: z.array(z.string()),
  risk: z.enum(["low", "medium", "high", "critical"])
});

export const CommandCenterDemoStepSchema = z.object({
  id: z.string(),
  label: z.string(),
  route: z.string(),
  status: z.enum(["ready", "blocked"]),
  what_it_proves: z.string(),
  operator_prompt: z.string(),
  source_item_ids: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  action_ids: z.array(z.string())
});

export const CommandCenterActionPlanItemSchema = z.object({
  id: z.string(),
  title: z.string(),
  route: z.string(),
  status: z.enum(["ready", "blocked"]),
  priority: z.number(),
  category: z.string(),
  why_it_matters: z.string(),
  operator_action: z.string(),
  skill_id: z.string().nullable().optional(),
  codex_prompt: z.string().nullable().optional(),
  codex_context_endpoint: z.string().nullable().optional(),
  expected_codex_output: z.string().nullable().optional(),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  action_ids: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  risk: z.enum(["low", "medium", "high", "critical"])
});

export const DailyDecisionSchema = z.object({
  id: z.string(),
  title: z.string(),
  route: z.string(),
  status: z.enum(["ready", "blocked"]),
  priority: z.number(),
  metric_tiles: z.record(z.union([z.string(), z.number()])),
  co_widzimy: z.string(),
  dlaczego_to_ma_znaczenie: z.string(),
  bezpieczny_next_step: z.string(),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  action_ids: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  skill_id: z.string().nullable().optional(),
  codex_prompt: z.string().nullable().optional(),
  codex_context_endpoint: z.string().nullable().optional(),
  expected_codex_output: z.string().nullable().optional(),
  risk: z.enum(["low", "medium", "high", "critical"])
});

export const CommandCenterResponseSchema = z.object({
  generated_at: z.string().nullable().optional(),
  strict_instruction: z.string(),
  primary_next_step: z.string(),
  blocker_count: z.number(),
  tactical_item_count: z.number(),
  daily_decisions: z.array(DailyDecisionSchema),
  operator_brief: z.array(CommandCenterBriefItemSchema),
  demo_script: z.array(CommandCenterDemoStepSchema),
  action_plan: z.array(CommandCenterActionPlanItemSchema),
  connector_summary: ConnectorSummarySchema,
  sections: z.record(z.array(OpportunitySchema)),
  active_actions: z.array(ActionObjectSchema),
  connector_health: z.array(ConnectorStatusSchema),
  codex_operator_status: z.record(z.unknown())
});

export const WorkflowSchema = z.object({
  id: z.string(),
  label: z.string(),
  description: z.string(),
  steps: z
    .array(
      z.object({
        id: z.string(),
        label: z.string(),
        required_connectors: z.array(z.string()),
        output_contract: z.string()
      })
    )
    .default([]),
  status: z.enum(["ready", "blocked", "planned"]).default("planned"),
  route: z.string().nullable().optional(),
  skill_id: z.string().nullable().optional(),
  safe_next_step: z.string().nullable().optional(),
  source_connectors: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()).default([]),
  action_ids: z.array(z.string()).default([]),
  blocked_claims: z.array(z.string()).default([]),
  metric_tiles: z.record(z.union([z.string(), z.number()])).default({}),
  missing_contracts: z.array(z.string()).default([]),
  risk: z.enum(["low", "medium", "high"]).default("low")
});

export const DemandGenReadinessContractSchema = z.object({
  status: z.enum(["ready", "blocked"]),
  title: z.string(),
  summary: z.string(),
  metric_tiles: z.record(z.union([z.string(), z.number()])).default({}),
  available_read_contracts: z.array(z.string()),
  missing_read_contracts: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  action_ids: z.array(z.string()),
  operator_review_gates: z.array(z.string()),
  campaign_rows_evaluated: z.number(),
  campaign_channel_counts: z.record(z.number()),
  demand_gen_campaign_rows: z.array(AdsCampaignMetricRowSchema),
  next_step: z.string(),
  risk: z.enum(["low", "medium", "high"])
});

export const WorkflowInputSchema = z.object({
  connector_ids: z.array(z.string()),
  parameters: z.record(z.unknown())
});

export const WorkflowOutputSchema = z.object({
  evidence_ids: z.array(z.string()),
  action_ids: z.array(z.string()),
  errors: z.array(z.string())
});

export const WorkflowRunSchema = z.object({
  id: z.string(),
  workflow_id: z.string(),
  status: z.enum(["queued", "running", "completed", "failed", "blocked"]),
  started_at: z.string(),
  completed_at: z.string().nullable().optional(),
  input: WorkflowInputSchema,
  output: WorkflowOutputSchema
});

export const ContextPackResponseSchema = z.object({
  current_product_rules: z.array(z.string()),
  available_connectors: z.array(z.string()),
  connector_status: z.array(ConnectorStatusSchema),
  top_opportunities: z.array(OpportunitySchema),
  active_action_objects: z.array(ActionObjectSchema),
  connector_refresh_runs: z.array(ConnectorRefreshRunSchema),
  evidence_summaries: z.array(EvidenceSchema),
  knowledge_card_summaries: z.array(KnowledgeCardSchema),
  expert_rule_summaries: z.array(ExpertRuleSummarySchema),
  expert_capabilities: z.array(ExpertCapabilitySchema),
  command_center: CommandCenterResponseSchema,
  marketing_brief: MarketingBriefSchema,
  tactical_queue: TacticalQueueResponseSchema,
  ads_diagnostics: AdsDiagnosticsResponseSchema,
  merchant_diagnostics: MerchantDiagnosticsResponseSchema,
  content_diagnostics: ContentDiagnosticsResponseSchema,
  ga4_diagnostics: Ga4DiagnosticsResponseSchema,
  localo_diagnostics: LocaloDiagnosticsResponseSchema.optional(),
  ahrefs_diagnostics: AhrefsDiagnosticsResponseSchema.optional(),
  demand_gen_readiness: DemandGenReadinessContractSchema.optional(),
  strict_instruction: z.string()
});

export type ConnectorStatus = z.infer<typeof ConnectorStatusSchema>;
export type MetricFact = z.infer<typeof MetricFactSchema>;
export type MetricStoreStatus = z.infer<typeof MetricStoreStatusSchema>;
export type Evidence = z.infer<typeof EvidenceSchema>;
export type ConnectorRefreshRun = z.infer<typeof ConnectorRefreshRunSchema>;
export type Opportunity = z.infer<typeof OpportunitySchema>;
export type ActionObject = z.infer<typeof ActionObjectSchema>;
export type ActionValidationResult = z.infer<typeof ActionValidationResultSchema>;
export type ActionMutationAuditRecord = z.infer<typeof ActionMutationAuditRecordSchema>;
export type ActionApplyResult = z.infer<typeof ActionApplyResultSchema>;
export type ActionPreviewRequest = z.infer<typeof ActionPreviewRequestSchema>;
export type ActionPreviewResult = z.infer<typeof ActionPreviewResultSchema>;
export type ActionReviewRequest = z.infer<typeof ActionReviewRequestSchema>;
export type ActionReviewResult = z.infer<typeof ActionReviewResultSchema>;
export type ActionConfirmRequest = z.infer<typeof ActionConfirmRequestSchema>;
export type ActionConfirmResult = z.infer<typeof ActionConfirmResultSchema>;
export type ActionImpactCheckRequest = z.infer<typeof ActionImpactCheckRequestSchema>;
export type ActionImpactCheckResult = z.infer<typeof ActionImpactCheckResultSchema>;
export type ActionApplyRequest = z.infer<typeof ActionApplyRequestSchema>;
export type CommandCenterResponse = z.infer<typeof CommandCenterResponseSchema>;
export type CommandCenterBriefItem = z.infer<typeof CommandCenterBriefItemSchema>;
export type CommandCenterDemoStep = z.infer<typeof CommandCenterDemoStepSchema>;
export type CommandCenterActionPlanItem = z.infer<typeof CommandCenterActionPlanItemSchema>;
export type DailyDecision = z.infer<typeof DailyDecisionSchema>;
export type AdsDiagnosticSection = z.infer<typeof AdsDiagnosticSectionSchema>;
export type AdsAccountCurrencyReadContract = z.infer<
  typeof AdsAccountCurrencyReadContractSchema
>;
export type AdsBudgetPacingRow = z.infer<typeof AdsBudgetPacingRowSchema>;
export type AdsBudgetPacingReadContract = z.infer<
  typeof AdsBudgetPacingReadContractSchema
>;
export type AdsCustomSegmentCandidate = z.infer<typeof AdsCustomSegmentCandidateSchema>;
export type AdsCustomSegmentsReadContract = z.infer<
  typeof AdsCustomSegmentsReadContractSchema
>;
export type AdsKeywordMatchContextRow = z.infer<
  typeof AdsKeywordMatchContextRowSchema
>;
export type AdsKeywordMatchContextReadContract = z.infer<
  typeof AdsKeywordMatchContextReadContractSchema
>;
export type AdsNegativeKeywordPayloadPreview = z.infer<
  typeof AdsNegativeKeywordPayloadPreviewSchema
>;
export type AdsNegativeKeywordCandidate = z.infer<
  typeof AdsNegativeKeywordCandidateSchema
>;
export type AdsNegativeKeywordsReadContract = z.infer<
  typeof AdsNegativeKeywordsReadContractSchema
>;
export type AdsDiagnosticsResponse = z.infer<typeof AdsDiagnosticsResponseSchema>;
export type MerchantDiagnosticSection = z.infer<typeof MerchantDiagnosticSectionSchema>;
export type MerchantDecisionItem = z.infer<typeof MerchantDecisionItemSchema>;
export type MerchantDiagnosticsResponse = z.infer<typeof MerchantDiagnosticsResponseSchema>;
export type ContentDiagnosticSection = z.infer<typeof ContentDiagnosticSectionSchema>;
export type ContentDiagnosticsResponse = z.infer<typeof ContentDiagnosticsResponseSchema>;
export type Ga4DecisionItem = z.infer<typeof Ga4DecisionItemSchema>;
export type Ga4DiagnosticSection = z.infer<typeof Ga4DiagnosticSectionSchema>;
export type Ga4DiagnosticsResponse = z.infer<typeof Ga4DiagnosticsResponseSchema>;
export type LocaloAccessProbe = z.infer<typeof LocaloAccessProbeSchema>;
export type LocaloDecisionItem = z.infer<typeof LocaloDecisionItemSchema>;
export type LocaloDiagnosticSection = z.infer<typeof LocaloDiagnosticSectionSchema>;
export type LocaloDiagnosticsResponse = z.infer<typeof LocaloDiagnosticsResponseSchema>;
export type AhrefsDecisionItem = z.infer<typeof AhrefsDecisionItemSchema>;
export type AhrefsDiagnosticSection = z.infer<typeof AhrefsDiagnosticSectionSchema>;
export type AhrefsDiagnosticsResponse = z.infer<typeof AhrefsDiagnosticsResponseSchema>;
export type MarketingBrief = z.infer<typeof MarketingBriefSchema>;
export type MarketingBriefItem = z.infer<typeof MarketingBriefItemSchema>;
export type MarketingBriefSection = z.infer<typeof MarketingBriefSectionSchema>;
export type TacticalQueueItem = z.infer<typeof TacticalQueueItemSchema>;
export type TacticalQueueResponse = z.infer<typeof TacticalQueueResponseSchema>;
export type Workflow = z.infer<typeof WorkflowSchema>;
export type WorkflowRun = z.infer<typeof WorkflowRunSchema>;
export type DemandGenReadinessContract = z.infer<typeof DemandGenReadinessContractSchema>;
export type ContextPackResponse = z.infer<typeof ContextPackResponseSchema>;
export type ExpertRule = z.infer<typeof ExpertRuleSchema>;
export type ExpertRuleSummary = z.infer<typeof ExpertRuleSummarySchema>;
export type ExpertCapability = z.infer<typeof ExpertCapabilitySchema>;
export type KnowledgeCard = z.infer<typeof KnowledgeCardSchema>;
export type KnowledgeDecisionBinding = z.infer<typeof KnowledgeDecisionBindingSchema>;
export type KnowledgeOperatingMapResponse = z.infer<typeof KnowledgeOperatingMapResponseSchema>;
export type MarketingPlaybook = z.infer<typeof MarketingPlaybookSchema>;
export type KnowledgeCompilerResult = z.infer<typeof KnowledgeCompilerResultSchema>;
