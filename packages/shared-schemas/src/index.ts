import { z } from "zod";

export const ConnectorStatusSchema = z.object({
  id: z.string(),
  label: z.string(),
  status: z.string(),
  status_label: z.string().default(""),
  configured: z.boolean(),
  missing_credentials: z.array(z.string()),
  available_credential_sources: z.array(z.string()),
  freshness: z.object({
    state: z.string(),
    notes: z.string().nullable().optional()
  }),
  supported_actions: z.array(z.string())
});

export const FreshnessStateSchema = z.object({
  state: z.enum(["fresh", "stale", "unknown", "missing"]),
  last_success_at: z.string().nullable().optional(),
  checked_at: z.string().nullable().optional(),
  notes: z.string().nullable().optional()
});

export const DecisionStateSchema = z.enum(["ready", "stale", "blocked", "missing", "unknown"]);

export const MetricFactSchema = z.object({
  name: z.string(),
  metric_label: z.string().default(""),
  value: z.union([z.string(), z.number()]),
  period: z.string(),
  source_connector: z.string(),
  evidence_id: z.string(),
  dimensions: z.record(z.string()).optional().default({}),
  dimension_labels: z.record(z.string()).optional().default({}),
  dimension_value_labels: z.record(z.string()).optional().default({}),
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
  title_label: z.string().default(""),
  source_connector: z.string(),
  source_connector_label: z.string().default(""),
  source_type: z.string(),
  source_type_label: z.string().default(""),
  source_id: z.string(),
  collected_at: z.string(),
  freshness: z.object({
    state: z.string(),
    notes: z.string().nullable().optional()
  }),
  freshness_label: z.string().default(""),
  summary: z.string(),
  trace_summary_label: z.string().default(""),
  raw_ref: z.string().nullable().optional()
});

export const ConnectorRefreshRunSchema = z.object({
  id: z.string(),
  connector_id: z.string(),
  mode: z.enum(["status_probe", "vendor_read"]),
  status: z.enum(["completed", "blocked", "failed"]),
  status_label: z.string().default(""),
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
  domain_label: z.string().default(""),
  source_connectors: z.array(z.string()).min(1),
  source_connector_labels: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()).min(1),
  evidence_summary_label: z.string().default(""),
  metric_tiles: z.record(z.union([z.string(), z.number()])).default({}),
  metrics: z.array(MetricFactSchema),
  human_diagnosis: z.string().min(1),
  recommended_action: z.string(),
  risk: z.string(),
  risk_label: z.string().default(""),
  action_ids: z.array(z.string()),
  action_summary_label: z.string().default(""),
  expert_rule_ids: z.array(z.string()),
  playbook_ids: z.array(z.string()),
  knowledge_summary_label: z.string().default(""),
  is_fixture: z.boolean()
});

export const AuditEventSchema = z.object({
  id: z.string(),
  action_id: z.string().nullable().optional(),
  event_type: z.string(),
  event_type_label: z.string().default(""),
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
  status_label: z.string().default(""),
  summary: z.string().default("Wymaga sprawdzenia w WILQ przed kolejnym krokiem."),
  required_checks: z.array(z.string()).default([]),
  required_check_labels: z.array(z.string()).default([]),
  operator_checklist: z.array(z.string()).default([]),
  operator_checklist_labels: z.array(z.string()).default([]),
  apply_blockers: z.array(z.string()).default([]),
  apply_blocker_labels: z.array(z.string()).default([]),
  confirmation_required: z.boolean().default(true),
  apply_allowed: z.boolean().default(false),
  last_review_outcome: ActionReviewOutcomeSchema.nullable().optional(),
  last_review_outcome_label: z.string().nullable().optional(),
  last_reviewed_by: z.string().nullable().optional(),
  last_reviewed_at: z.string().nullable().optional(),
  last_review_summary: z.string().nullable().optional(),
  last_confirmation_by: z.string().nullable().optional(),
  last_confirmation_at: z.string().nullable().optional(),
  last_confirmation_summary: z.string().nullable().optional(),
  last_impact_check_status: z.enum(["checked", "blocked"]).nullable().optional(),
  last_impact_check_status_label: z.string().nullable().optional(),
  last_impact_checked_by: z.string().nullable().optional(),
  last_impact_checked_at: z.string().nullable().optional(),
  last_impact_check_summary: z.string().nullable().optional(),
  last_mutation_audit_id: z.string().nullable().optional(),
  last_mutation_audit_status: z.enum(["blocked", "applied", "failed"]).nullable().optional(),
  last_mutation_audit_status_label: z.string().nullable().optional(),
  last_mutation_audit_actor: z.string().nullable().optional(),
  last_mutation_audit_at: z.string().nullable().optional(),
  last_mutation_audit_summary: z.string().nullable().optional(),
  last_mutation_attempted: z.boolean().nullable().optional(),
  last_mutation_adapter: z.string().nullable().optional(),
  last_mutation_audit_event_id: z.string().nullable().optional(),
  last_mutation_blockers: z.array(z.string()).default([]),
  last_mutation_blocker_labels: z.array(z.string()).default([])
});

export const ActionPreviewRowViewModelSchema = z.object({
  label: z.string(),
  value: z.string()
});

export const ActionPreviewCardViewModelSchema = z.object({
  id: z.string(),
  kind: z.string(),
  title_label: z.string(),
  subtitle_label: z.string().default(""),
  status_label: z.string().default(""),
  rows: z.array(ActionPreviewRowViewModelSchema).default([]),
  apply_state_label: z.string().default(""),
  system_readiness_label: z.string().default("")
});

export const ActionPreviewItemViewModelSchema = z.object({
  id: z.string(),
  title_label: z.string(),
  status_label: z.string().default(""),
  rows: z.array(ActionPreviewRowViewModelSchema).default([])
});

export const ActionObjectSchema = z.object({
  id: z.string(),
  title: z.string(),
  domain: z.string(),
  connector: z.string(),
  connector_label: z.string().default(""),
  mode: z.enum(["suggest", "prepare", "apply"]),
  mode_label: z.string().default(""),
  risk: z.enum(["low", "medium", "high", "critical"]),
  risk_label: z.string().default(""),
  status: z.string(),
  status_label: z.string().default(""),
  evidence_ids: z.array(z.string()).min(1),
  evidence_summary_label: z.string().default(""),
  metrics: z.array(MetricFactSchema),
  human_diagnosis: z.string(),
  recommended_reason: z.string(),
  validation_status: z.string(),
  validation_status_label: z.string().default(""),
  review_gate: ActionReviewGateSchema.optional().default({}),
  preview_cards: z.array(ActionPreviewCardViewModelSchema).default([]),
  payload: z.record(z.unknown()),
  audit_events: z.array(AuditEventSchema)
});

export const ActionValidationResultSchema = z.object({
  action_id: z.string(),
  valid: z.boolean(),
  status: z.enum(["valid", "invalid"]),
  status_label: z.string().default(""),
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
  status_label: z.string().default(""),
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
  status_label: z.string().default(""),
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
  status_label: z.string().default(""),
  dry_run: z.boolean(),
  mutation_allowed: z.boolean(),
  preview_contract: z.string().nullable().optional(),
  preview_items: z.array(ActionPreviewItemViewModelSchema),
  preview_cards: z.array(ActionPreviewCardViewModelSchema).default([]),
  preview_items_total: z.number(),
  omitted_items: z.number(),
  blockers: z.array(z.string()),
  blocker_labels: z.array(z.string()).default([]),
  audit_event: AuditEventSchema,
  review_gate: ActionReviewGateSchema
});

export const ActionReviewResultSchema = z.object({
  action_id: z.string(),
  status: z.enum(["recorded"]),
  status_label: z.string().default(""),
  audit_event: AuditEventSchema,
  review_gate: ActionReviewGateSchema
});

export const ActionConfirmRequestSchema = z.object({
  confirmed_by: z.string().min(1),
  notes: z.string().min(1).max(2000),
  preview_acknowledged: z.boolean().default(false),
  target_roas: z.number().positive().nullable().optional(),
  target_cpa_micros: z.number().int().positive().nullable().optional()
});

export const ActionConfirmResultSchema = z.object({
  action_id: z.string(),
  confirmed: z.boolean(),
  status: z.enum(["confirmed", "blocked"]),
  status_label: z.string().default(""),
  blockers: z.array(z.string()),
  blocker_labels: z.array(z.string()).default([]),
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
  status_label: z.string().default(""),
  pre_window_days: z.number(),
  post_window_days: z.number(),
  metric_fact_count: z.number(),
  source_connectors: z.array(z.string()),
  source_connector_labels: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  blockers: z.array(z.string()),
  blocker_labels: z.array(z.string()).default([]),
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
  kind_label: z.string().default(""),
  priority: z.number(),
  priority_label: z.string().default(""),
  source_connectors: z.array(z.string()),
  source_connector_labels: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  metric_facts: z.array(MetricFactSchema),
  metric_fact_labels: z.record(z.string()).default({}),
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
  dimensions: z.record(z.string()).optional().default({}),
  dimension_labels: z.record(z.string()).optional().default({}),
  dimension_value_labels: z.record(z.string()).optional().default({}),
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

export const AdsDiagnosticSectionSchema = z.object({
  id: z.string(),
  title: z.string(),
  status: z.enum(["ready", "blocked", "missing"]),
  status_label: z.string().default(""),
  summary: z.string(),
  diagnosis: z.string(),
  next_step: z.string(),
  source_connectors: z.array(z.string()),
  source_connector_labels: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  metric_facts: z.array(MetricFactSchema),
  metric_fact_labels: z.record(z.string()).default({}),
  action_ids: z.array(z.string()),
  action_summary_label: z.string().default(""),
  knowledge_card_ids: z.array(z.string()).optional().default([]),
  expert_rule_ids: z.array(z.string()).optional().default([]),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).default([]),
  risk: z.enum(["low", "medium", "high", "critical"])
});

export const AdsBlockedHandoffSchema = z.object({
  id: z.string(),
  status: z.enum(["ready", "blocked"]),
  status_label: z.string().optional().default(""),
  title: z.string(),
  summary: z.string(),
  marketer_message: z.string(),
  repair_steps: z.array(z.string()),
  allowed_demo_claims: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).default([]),
  source_connectors: z.array(z.string()),
  source_connector_labels: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  action_ids: z.array(z.string()),
  action_summary_label: z.string().default("")
});

export const AdsCampaignMetricRowSchema = z.object({
  campaign_id: z.string().nullable().optional(),
  campaign_name: z.string(),
  campaign_status: z.string().nullable().optional(),
  campaign_status_label: z.string().optional().default(""),
  advertising_channel_type: z.string().nullable().optional(),
  advertising_channel_type_label: z.string().optional().default(""),
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
  human_review_gates: z.array(z.string()).default([]),
  human_review_gate_labels: z.array(z.string()).optional().default([])
});

export const AdsCampaignReadContractSchema = z.object({
  id: z.string(),
  status: z.enum(["ready", "blocked"]),
  status_label: z.string().optional().default(""),
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
  status_label: z.string().optional().default(""),
  summary: z.string(),
  allowed_uses: z.array(z.string()),
  allowed_use_labels: z.array(z.string()).optional().default([]),
  blocked_uses: z.array(z.string()),
  blocked_use_labels: z.array(z.string()).optional().default([]),
  missing_requirements: z.array(z.string()),
  missing_requirement_labels: z.array(z.string()).optional().default([]),
  required_validation: z.array(z.string()),
  required_validation_labels: z.array(z.string()).optional().default([]),
  policy_ids: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  action_ids: z.array(z.string()).optional().default([]),
  apply_allowed: z.boolean(),
  destructive: z.boolean()
});

export const AdsStrategyReviewReadinessContractSchema = z.object({
  id: z.string(),
  status: z.enum(["ready", "blocked"]),
  status_label: z.string().optional().default(""),
  title: z.string(),
  summary: z.string(),
  latest_review_status: z
    .enum(["missing", "approved_for_prepare", "needs_changes", "rejected", "deferred"])
    .optional()
    .default("missing"),
  latest_review_status_label: z.string().optional().default(""),
  latest_review_outcome: z
    .enum(["approved_for_prepare", "needs_changes", "rejected", "deferred"])
    .nullable()
    .optional(),
  reviewed_by: z.string().nullable().optional(),
  reviewed_at: z.string().nullable().optional(),
  current_context: z.record(
    z.union([z.string(), z.number(), z.boolean(), z.array(z.string()), z.null()])
  ),
  required_validation: z.array(z.string()),
  required_validation_labels: z.array(z.string()).optional().default([]),
  missing_read_contracts: z.array(z.string()),
  missing_read_contract_labels: z.array(z.string()).optional().default([]),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([]),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  action_ids: z.array(z.string()),
  apply_allowed: z.boolean(),
  destructive: z.boolean(),
  next_step: z.string()
});

export const AdsBusinessContextReadContractSchema = z.object({
  id: z.string(),
  status: z.enum(["ready", "blocked"]),
  status_label: z.string().default(""),
  title: z.string(),
  summary: z.string(),
  profit_margin: z.number().nullable().optional(),
  business_goal: z.string().nullable().optional(),
  budget_goal: z.string().nullable().optional(),
  target_roas: z.number().nullable().optional(),
  target_cpa_micros: z.number().nullable().optional(),
  strategy_review_status: z
    .enum(["missing", "approved_for_prepare", "needs_changes", "rejected", "deferred"])
    .optional()
    .default("missing"),
  strategy_reviewed_by: z.string().nullable().optional(),
  strategy_reviewed_at: z.string().nullable().optional(),
  strategy_review_summary: z.string().nullable().optional(),
  configured_sources: z.array(z.string()),
  business_policy_ids: z.array(z.string()).optional().default([]),
  operator_review_gates: z.array(z.string()).optional().default([]),
  operator_review_gate_labels: z.array(z.string()).optional().default([]),
  target_interpretation: AdsBusinessTargetInterpretationSchema,
  strategy_review_readiness_contract: AdsStrategyReviewReadinessContractSchema,
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
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([])
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
  status_label: z.string().optional().default(""),
  reason: z.string(),
  max_allowed_delta_percent: z.number(),
  current_budget_amount_micros: z.number().nullable().optional(),
  proposed_budget_amount_micros: z.number().nullable().optional(),
  proposed_delta_percent: z.number().nullable().optional(),
  missing_requirements: z.array(z.string()),
  missing_requirement_labels: z.array(z.string()).optional().default([]),
  required_validation: z.array(z.string()),
  required_validation_labels: z.array(z.string()).optional().default([]),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([]),
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
  operation_type_label: z.string().optional().default(""),
  current_budget_amount_micros: z.number().nullable().optional(),
  proposed_budget_amount_micros: z.number().nullable().optional(),
  proposed_budget_delta_micros: z.number().nullable().optional(),
  reason: z.string(),
  evidence_ids: z.array(z.string()),
  source_metric_names: z.array(z.string()),
  required_validation: z.array(z.string()),
  required_validation_labels: z.array(z.string()).optional().default([]),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([]),
  safety_review: AdsBudgetApplySafetyReviewSchema,
  api_mutation_ready: z.boolean(),
  apply_allowed: z.boolean(),
  destructive: z.boolean()
});

export const AdsBudgetPacingRowSchema = z.object({
  campaign_id: z.string().nullable().optional(),
  campaign_name: z.string(),
  campaign_status: z.string().nullable().optional(),
  campaign_status_label: z.string().optional().default(""),
  advertising_channel_type: z.string().nullable().optional(),
  advertising_channel_type_label: z.string().optional().default(""),
  budget_id: z.string().nullable().optional(),
  budget_name: z.string().nullable().optional(),
  budget_period: z.string().nullable().optional(),
  budget_period_label: z.string().optional().default(""),
  budget_status: z.string().nullable().optional(),
  budget_status_label: z.string().optional().default(""),
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
  preview_card: ActionPreviewCardViewModelSchema.nullable().optional(),
  missing_metrics: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([])
});

export const AdsSharedBudgetCampaignShareSchema = z.object({
  campaign_id: z.string().nullable().optional(),
  campaign_name: z.string(),
  campaign_status: z.string().nullable().optional(),
  campaign_status_label: z.string().optional().default(""),
  advertising_channel_type: z.string().nullable().optional(),
  advertising_channel_type_label: z.string().optional().default(""),
  cost_micros_7d: z.number().nullable().optional(),
  spend_share_7d: z.number().nullable().optional(),
  evidence_ids: z.array(z.string())
});

export const AdsSharedBudgetDistributionRowSchema = z.object({
  budget_id: z.string(),
  budget_name: z.string().nullable().optional(),
  campaign_count: z.number(),
  budget_amount_micros: z.number().nullable().optional(),
  seven_day_budget_micros: z.number().nullable().optional(),
  total_cost_micros_7d: z.number().nullable().optional(),
  spend_to_budget_ratio_7d: z.number().nullable().optional(),
  campaign_shares: z.array(AdsSharedBudgetCampaignShareSchema),
  evidence_ids: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([])
});

export const AdsBudgetPacingReadContractSchema = z.object({
  id: z.string(),
  status: z.enum(["ready", "blocked"]),
  title: z.string(),
  summary: z.string(),
  empty_state_message: z.string().optional().default(""),
  allowed_metrics: z.array(z.string()),
  missing_read_contracts: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  budget_rows: z.array(AdsBudgetPacingRowSchema),
  shared_budget_distribution_rows: z.array(AdsSharedBudgetDistributionRowSchema)
    .optional()
    .default([]),
  payload_preview: z.array(AdsBudgetApplyPreviewSchema),
  action_ids: z.array(z.string()),
  next_step: z.string()
});

export const AdsRecommendationApplyPreviewSchema = z.object({
  id: z.string(),
  recommendation_id: z.string().nullable().optional(),
  recommendation_resource_name: z.string().nullable().optional(),
  recommendation_type: z.string(),
  recommendation_type_label: z.string().optional().default(""),
  campaign_id: z.string().nullable().optional(),
  campaign_budget_id: z.string().nullable().optional(),
  operation_type: z.literal("ApplyRecommendationOperation"),
  operation_type_label: z.string().optional().default(""),
  reason: z.string(),
  evidence_ids: z.array(z.string()),
  source_metric_names: z.array(z.string()),
  required_validation: z.array(z.string()),
  required_validation_labels: z.array(z.string()).optional().default([]),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([]),
  api_mutation_ready: z.boolean(),
  apply_allowed: z.boolean(),
  destructive: z.boolean()
});

export const AdsRecommendationRowSchema = z.object({
  recommendation_id: z.string().nullable().optional(),
  recommendation_resource_name: z.string().nullable().optional(),
  recommendation_type: z.string(),
  recommendation_type_label: z.string().optional().default(""),
  review_priority: z
    .enum(["pilne", "wysokie", "normalne", "niski sygnał"])
    .default("normalne"),
  review_score: z.number().min(0).max(100).default(0),
  review_reason: z.string(),
  human_review_gates: z.array(z.string()).default([]),
  human_review_gate_labels: z.array(z.string()).optional().default([]),
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
  preview_card: ActionPreviewCardViewModelSchema.nullable().optional(),
  missing_metrics: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([])
});

export const AdsRecommendationsReadContractSchema = z.object({
  id: z.string(),
  status: z.enum(["ready", "blocked"]),
  title: z.string(),
  summary: z.string(),
  allowed_metrics: z.array(z.string()),
  missing_read_contracts: z.array(z.string()),
  operator_review_gates: z.array(z.string()).optional().default([]),
  operator_review_gate_labels: z.array(z.string()).optional().default([]),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([]),
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
  campaign_status_label: z.string().optional().default(""),
  advertising_channel_type: z.string().nullable().optional(),
  advertising_channel_type_label: z.string().optional().default(""),
  search_impression_share: z.number().nullable().optional(),
  search_budget_lost_impression_share: z.number().nullable().optional(),
  search_rank_lost_impression_share: z.number().nullable().optional(),
  evidence_ids: z.array(z.string()),
  metric_facts: z.array(MetricFactSchema),
  missing_metrics: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([])
});

export const AdsImpressionShareReadContractSchema = z.object({
  id: z.string(),
  status: z.enum(["ready", "blocked"]),
  title: z.string(),
  summary: z.string(),
  empty_state_message: z.string().optional().default(""),
  allowed_metrics: z.array(z.string()),
  missing_read_contracts: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  impression_share_rows: z.array(AdsImpressionShareRowSchema),
  next_step: z.string()
});

export const AdsCampaignTriageRowSchema = z.object({
  campaign_id: z.string().nullable().optional(),
  campaign_name: z.string(),
  campaign_status: z.string().nullable().optional(),
  campaign_status_label: z.string().nullable().optional(),
  advertising_channel_type: z.string().nullable().optional(),
  advertising_channel_type_label: z.string().nullable().optional(),
  review_priority: z
    .enum(["pilne", "wysokie", "normalne", "niski sygnał"])
    .default("niski sygnał"),
  review_score: z.number().min(0).max(100).default(0),
  review_reason: z.string(),
  next_step: z.string(),
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
  clicks: z.number().nullable().optional(),
  impressions: z.number().nullable().optional(),
  cost_micros: z.number().nullable().optional(),
  conversions: z.number().nullable().optional(),
  conversion_value: z.number().nullable().optional(),
  ctr: z.number().nullable().optional(),
  average_cpc_micros: z.number().nullable().optional(),
  conversion_rate: z.number().nullable().optional(),
  cost_per_conversion_micros: z.number().nullable().optional(),
  roas: z.number().nullable().optional(),
  spend_to_budget_ratio_7d: z.number().nullable().optional(),
  search_budget_lost_impression_share: z.number().nullable().optional(),
  recommendation_count: z.number().int().nonnegative().default(0),
  recommendation_types: z.array(z.string()).default([]),
  has_budget_apply_preview: z.boolean().default(false),
  has_recommendation_apply_preview: z.boolean().default(false),
  evidence_ids: z.array(z.string()),
  action_ids: z.array(z.string()),
  source_metric_names: z.array(z.string()),
  missing_read_contracts: z.array(z.string()),
  missing_read_contract_labels: z.array(z.string()).optional().default([]),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([]),
  human_review_gates: z.array(z.string()).default([]),
  human_review_gate_labels: z.array(z.string()).optional().default([])
});

export const AdsCampaignTriageReadContractSchema = z.object({
  id: z.string(),
  status: z.enum(["ready", "blocked"]),
  title: z.string(),
  summary: z.string(),
  allowed_metrics: z.array(z.string()),
  missing_read_contracts: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  triage_rows: z.array(AdsCampaignTriageRowSchema),
  action_ids: z.array(z.string()),
  next_step: z.string()
});

export const AdsOptimizerReadinessItemSchema = z.object({
  id: z.string(),
  label: z.string().optional().default(""),
  title: z.string(),
  status: z.enum(["ready", "blocked"]),
  status_label: z.string().optional().default(""),
  summary: z.string(),
  next_step: z.string(),
  source_contract_ids: z.array(z.string()),
  allowed_metrics: z.array(z.string()),
  missing_read_contracts: z.array(z.string()),
  missing_read_contract_labels: z.array(z.string()).optional().default([]),
  operator_review_gates: z.array(z.string()).optional().default([]),
  operator_review_gate_labels: z.array(z.string()).optional().default([]),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([]),
  source_connectors: z.array(z.string()),
  source_connector_labels: z.array(z.string()).optional().default([]),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().optional().default(""),
  action_ids: z.array(z.string()),
  action_summary_label: z.string().optional().default(""),
  risk: z.enum(["low", "medium", "high", "critical"]),
  risk_label: z.string().optional().default("")
});

export const AdsOptimizerReadinessContractSchema = z.object({
  id: z.string(),
  status: z.enum(["review_ready", "blocked"]),
  status_label: z.string().optional().default(""),
  mode: z.literal("review_only"),
  mode_label: z.string().optional().default(""),
  title: z.string(),
  summary: z.string(),
  ready_area_count: z.number().int().nonnegative(),
  blocked_area_count: z.number().int().nonnegative(),
  readiness_items: z.array(AdsOptimizerReadinessItemSchema),
  allowed_metrics: z.array(z.string()),
  missing_read_contracts: z.array(z.string()),
  missing_read_contract_labels: z.array(z.string()).optional().default([]),
  operator_review_gates: z.array(z.string()).optional().default([]),
  operator_review_gate_labels: z.array(z.string()).optional().default([]),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([]),
  source_connectors: z.array(z.string()),
  source_connector_labels: z.array(z.string()).optional().default([]),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().optional().default(""),
  action_ids: z.array(z.string()),
  action_summary_label: z.string().optional().default(""),
  api_mutation_ready: z.boolean(),
  apply_allowed: z.boolean(),
  next_step: z.string()
});

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
  evidence_ids: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([])
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
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([]),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  readiness_rows: z.array(AdsChangeImpactReadinessRowSchema),
  action_ids: z.array(z.string()).optional().default([]),
  api_mutation_ready: z.boolean(),
  apply_allowed: z.boolean(),
  next_step: z.string()
});

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
  operator_review_gate_labels: z.array(z.string()).optional().default([]),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([]),
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
  blocked_claims: z.array(z.string())
});

export const AdsSearchTermReviewSummaryContractSchema = z.object({
  id: z.string(),
  status: z.enum(["ready", "blocked"]),
  title: z.string(),
  summary: z.string(),
  allowed_metrics: z.array(z.string()),
  missing_read_contracts: z.array(z.string()),
  operator_review_gates: z.array(z.string()).optional().default([]),
  operator_review_gate_labels: z.array(z.string()).optional().default([]),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([]),
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

export const AdsCustomSegmentTargetingPreviewSchema = z.object({
  id: z.string(),
  custom_segment_preview_id: z.string(),
  target_scope: z.literal("campaign_context_review"),
  campaign_id: z.string().nullable().optional(),
  campaign_name: z.string().nullable().optional(),
  operation_type: z.literal("custom_segment_targeting_review"),
  reason: z.string(),
  required_validation: z.array(z.string()),
  required_validation_labels: z.array(z.string()).optional().default([]),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([]),
  api_mutation_ready: z.boolean(),
  apply_allowed: z.boolean(),
  destructive: z.boolean()
});

export const AdsCustomSegmentApplySafetyReviewSchema = z.object({
  id: z.string(),
  custom_segment_preview_id: z.string(),
  safety_contract: z.literal("custom_segment_apply_safety_v1"),
  status: z.literal("blocked"),
  status_label: z.string().optional().default("zablokowane"),
  reason: z.string(),
  missing_requirements: z.array(z.string()),
  missing_requirement_labels: z.array(z.string()).optional().default([]),
  required_validation: z.array(z.string()),
  required_validation_labels: z.array(z.string()).optional().default([]),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([]),
  evidence_ids: z.array(z.string()),
  audit_required: z.boolean(),
  api_mutation_ready: z.boolean(),
  apply_allowed: z.boolean(),
  destructive: z.boolean()
});

export const AdsCustomSegmentPayloadPreviewSchema = z.object({
  id: z.string(),
  custom_segment_name: z.string(),
  member_type: z.literal("KEYWORD"),
  member_type_label: z.string().optional().default("słowa kluczowe"),
  source_terms: z.array(z.string()),
  campaign_id: z.string().nullable().optional(),
  campaign_name: z.string().nullable().optional(),
  reason: z.string(),
  evidence_ids: z.array(z.string()),
  source_metric_names: z.array(z.string()),
  required_validation: z.array(z.string()),
  required_validation_labels: z.array(z.string()).optional().default([]),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([]),
  targeting_preview: z.array(AdsCustomSegmentTargetingPreviewSchema).optional().default([]),
  safety_review: AdsCustomSegmentApplySafetyReviewSchema,
  api_mutation_ready: z.boolean(),
  apply_allowed: z.boolean(),
  destructive: z.boolean()
});

export const AdsCustomSegmentAudienceForecastRowSchema = z.object({
  id: z.string(),
  candidate_id: z.string(),
  custom_segment_name: z.string(),
  status: z.enum(["ready", "missing_forecast"]),
  forecast_available: z.boolean(),
  audience_size: z.number().int().nonnegative().nullable().optional(),
  source_terms: z.array(z.string()),
  reason: z.string(),
  evidence_ids: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([])
});

export const AdsCustomSegmentAudienceForecastReadContractSchema = z.object({
  id: z.string(),
  status: z.enum(["ready", "blocked"]),
  status_label: z.string().default(""),
  title: z.string(),
  summary: z.string(),
  checked_candidate_count: z.number().int().nonnegative(),
  forecast_row_count: z.number().int().nonnegative(),
  forecast_rows: z.array(AdsCustomSegmentAudienceForecastRowSchema),
  missing_read_contracts: z.array(z.string()),
  missing_read_contract_labels: z.array(z.string()).optional().default([]),
  operator_review_gates: z.array(z.string()).optional().default([]),
  operator_review_gate_labels: z.array(z.string()).optional().default([]),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([]),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  next_step: z.string()
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
  human_review_gate_labels: z.array(z.string()).optional().default([]),
  source_terms: z.array(z.string()),
  rejected_terms: z.array(z.string()),
  rejection_reasons: z.array(z.string()),
  source_quality: z
    .object({
      total_terms: z.number().int().nonnegative().default(0),
      accepted_terms: z.number().int().nonnegative().default(0),
      rejected_terms: z.number().int().nonnegative().default(0),
      missing_metric_terms: z.number().int().nonnegative().default(0),
      rejection_reasons: z.record(z.string(), z.number().int().nonnegative()).default({}),
      rejection_reason_labels: z.record(z.string(), z.number().int().nonnegative()).default({})
    })
    .default({
      total_terms: 0,
      accepted_terms: 0,
      rejected_terms: 0,
      missing_metric_terms: 0,
      rejection_reasons: {},
      rejection_reason_labels: {}
    }),
  search_term_rows: z.array(AdsSearchTermMetricRowSchema),
  keyword_planner_ideas: z.array(AdsKeywordPlannerIdeaRowSchema).optional().default([]),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  metric_facts: z.array(MetricFactSchema),
  confidence: z.enum(["low", "medium", "high"]),
  confidence_label: z.string().optional().default("niska"),
  validation_status: z.enum(["pending_validation", "blocked"]),
  validation_status_label: z.string().optional().default("do sprawdzenia"),
  payload_preview: AdsCustomSegmentPayloadPreviewSchema.nullable().optional(),
  preview_card: ActionPreviewCardViewModelSchema.nullable().optional(),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([]),
  next_step: z.string()
});

export const AdsCustomSegmentsReadContractSchema = z.object({
  id: z.string(),
  status: z.enum(["ready", "blocked"]),
  status_label: z.string().default(""),
  title: z.string(),
  summary: z.string(),
  candidates: z.array(AdsCustomSegmentCandidateSchema),
  payload_preview: z.array(AdsCustomSegmentPayloadPreviewSchema),
  audience_forecast_read_contract:
    AdsCustomSegmentAudienceForecastReadContractSchema,
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  missing_read_contracts: z.array(z.string()),
  missing_read_contract_labels: z.array(z.string()).optional().default([]),
  operator_review_gates: z.array(z.string()).optional().default([]),
  operator_review_gate_labels: z.array(z.string()).optional().default([]),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).optional().default([]),
  action_ids: z.array(z.string()),
  next_step: z.string()
});

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
  metric_tiles: z.record(z.union([z.string(), z.number()])).default({}),
  allowed_metrics: z.array(z.string()),
  missing_read_contracts: z.array(z.string()),
  missing_read_contract_labels: z.array(z.string()).default([]),
  operator_review_gates: z.array(z.string()).optional().default([]),
  operator_review_gate_labels: z.array(z.string()).optional().default([]),
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
  risk_label: z.string().default(""),
  risk: z.enum(["low", "medium", "high", "critical"])
});

export const AdsOperatorSummarySchema = z.object({
  id: z.literal("ads_operator_summary"),
  title: z.string(),
  summary: z.string(),
  next_step: z.string(),
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
  operator_review_gates: z.array(z.string()),
  operator_review_gate_labels: z.array(z.string()).optional().default([]),
  source_connectors: z.array(z.string()),
  source_connector_labels: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  action_ids: z.array(z.string()),
  action_summary_label: z.string().default(""),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).default([])
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
  action_ids: z.array(z.string()),
  blocker_count: z.number()
});

export const MerchantDiagnosticSectionSchema = z.object({
  id: z.string(),
  label: z.string().default(""),
  title: z.string(),
  status: z.enum(["ready", "blocked", "missing"]),
  status_label: z.string().default(""),
  summary: z.string(),
  diagnosis: z.string(),
  next_step: z.string(),
  source_connectors: z.array(z.string()),
  source_connector_labels: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  metric_facts: z.array(MetricFactSchema),
  tactical_items: z.array(TacticalQueueItemSchema),
  action_ids: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).default([]),
  risk: z.enum(["low", "medium", "high", "critical"]),
  risk_label: z.string().default("")
});

export const MerchantIssueClusterSchema = z.object({
  id: z.string(),
  issue_type: z.string(),
  issue_type_label: z.string().nullable().optional(),
  severity: z.string(),
  severity_label: z.string().nullable().optional(),
  resolution: z.string().nullable().optional(),
  resolution_label: z.string().nullable().optional(),
  affected_attribute: z.string().nullable().optional(),
  affected_attribute_label: z.string().nullable().optional(),
  country: z.string().nullable().optional(),
  reporting_context: z.string().nullable().optional(),
  reporting_context_label: z.string(),
  product_count: z.number(),
  count_semantics: z.literal("reported_issue_occurrences").default("reported_issue_occurrences"),
  sample_product_ids: z.array(z.string()),
  sample_titles: z.array(z.string()),
  sample_unavailable_reason: z.string().nullable().optional(),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  action_id: z.string().nullable().optional(),
  risk: z.enum(["low", "medium", "high", "critical"]),
  risk_label: z.string().default(""),
  next_step: z.string()
});

export const MerchantDecisionItemSchema = z.object({
  id: z.string(),
  decision_type: z.enum([
    "review_issue_cluster",
    "review_feed_status",
    "review_product_state_mapping",
    "review_price_impact_readiness",
    "block_until_vendor_read"
  ]),
  decision_type_label: z.string().default(""),
  status: z.enum(["ready", "blocked", "missing"]),
  status_label: z.string().default(""),
  title: z.string(),
  summary: z.string().nullable().optional(),
  cluster_id: z.string().nullable().optional(),
  issue_cluster_ids: z.array(z.string()).default([]),
  issue_type: z.string().nullable().optional(),
  issue_type_label: z.string().nullable().optional(),
  severity: z.string().nullable().optional(),
  severity_label: z.string().nullable().optional(),
  resolution: z.string().nullable().optional(),
  resolution_label: z.string().nullable().optional(),
  affected_attribute: z.string().nullable().optional(),
  affected_attribute_label: z.string().nullable().optional(),
  country: z.string().nullable().optional(),
  reporting_context: z.string().nullable().optional(),
  reporting_context_label: z.string().nullable().optional(),
  product_count: z.number().nullable().optional(),
  issue_count: z.number().nullable().optional(),
  count_semantics: z.literal("reported_issue_occurrences").default("reported_issue_occurrences"),
  priority: z.number(),
  priority_label: z.string().default(""),
  metric_tiles: z.record(z.union([z.string(), z.number()])).default({}),
  sample_product_ids: z.array(z.string()).default([]),
  sample_titles: z.array(z.string()).default([]),
  payload_preview: z.array(z.record(z.unknown())).default([]),
  preview_cards: z.array(ActionPreviewCardViewModelSchema).default([]),
  source_connectors: z.array(z.string()),
  source_connector_labels: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  metric_facts: z.array(MetricFactSchema),
  action_ids: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).default([]),
  rationale: z.string(),
  next_step: z.string(),
  why_it_matters: z.string().nullable().optional(),
  operator_action: z.string().nullable().optional(),
  risk: z.enum(["low", "medium", "high", "critical"]),
  risk_label: z.string().default("")
});

export const MerchantOperatorSummarySchema = z.object({
  id: z.literal("merchant_operator_summary"),
  title: z.string(),
  summary: z.string(),
  next_step: z.string(),
  top_decision_ids: z.array(z.string()),
  top_issue_cluster_ids: z.array(z.string()),
  top_tactical_item_ids: z.array(z.string()),
  reported_issue_occurrences: z.number(),
  decision_source: z.literal("decision_queue").default("decision_queue"),
  decision_source_label: z.string().default("kolejka decyzji Merchant"),
  drilldown_source: z.literal("issue_clusters").default("issue_clusters"),
  drilldown_source_label: z.string().default("grupy problemów feedu"),
  count_semantics: z.literal("reported_issue_occurrences").default("reported_issue_occurrences"),
  count_semantics_label: z.string().default("wystąpienia problemów w raportach"),
  issue_types: z.array(z.string()),
  source_connectors: z.array(z.string()),
  source_connector_labels: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  action_ids: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).default([])
});

export const MerchantFreshnessAssessmentSchema = z.object({
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

export const MerchantUnknownFactSchema = z.object({
  id: z.string(),
  title: z.string(),
  reason: z.string(),
  impact: z.string(),
  next_step: z.string(),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).default([])
});

export const MerchantProductSampleReadinessSchema = z.object({
  status: z.enum(["ready", "blocked"]),
  status_label: z.string().default(""),
  sample_products_available: z.boolean(),
  sample_count: z.number(),
  sample_product_ids: z.array(z.string()),
  sample_product_titles: z.array(z.string()),
  sample_summary_label: z.string().default(""),
  sample_title_labels: z.array(z.string()).default([]),
  current_read_contract: z.literal("merchant_aggregate_product_statuses"),
  required_read_contracts: z.array(z.string()),
  source_endpoint: z.string(),
  summary: z.string(),
  next_step: z.string(),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).default([])
});

export const MerchantProductPerformanceRowSchema = z.object({
  product_id: z.string(),
  title_label: z.string().default(""),
  product_reference_label: z.string().default(""),
  sample_title: z.string().nullable().optional(),
  issue_type: z.string().nullable().optional(),
  issue_type_label: z.string().nullable().optional(),
  affected_attribute: z.string().nullable().optional(),
  affected_attribute_label: z.string().nullable().optional(),
  country: z.string().nullable().optional(),
  reporting_context: z.string().nullable().optional(),
  reporting_context_label: z.string().nullable().optional(),
  source_connectors: z.array(z.string()),
  source_connector_labels: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  ads_product_title: z.string().nullable().optional(),
  ads_product_status: z.string().nullable().optional(),
  ads_product_status_label: z.string().default(""),
  ads_product_availability: z.string().nullable().optional(),
  ads_product_availability_label: z.string().default(""),
  ads_product_price_micros: z.number().nullable().optional(),
  ads_product_price_label: z.string().default(""),
  ads_product_currency_code: z.string().nullable().optional(),
  ads_product_previous_price_micros: z.number().nullable().optional(),
  ads_product_price_delta_micros: z.number().nullable().optional(),
  ads_product_price_delta_percent: z.number().nullable().optional(),
  ads_clicks: z.number().nullable().optional(),
  ads_cost_micros: z.number().nullable().optional(),
  ads_cost_label: z.string().default(""),
  ads_conversions: z.number().nullable().optional(),
  ads_conversion_value: z.number().nullable().optional(),
  ga4_ecommerce_purchases: z.number().nullable().optional(),
  ga4_purchase_revenue: z.number().nullable().optional(),
  missing_metrics: z.array(z.string()),
  missing_metric_labels: z.array(z.string()).default([]),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).default([])
});

export const MerchantProductPerformanceReadinessSchema = z.object({
  id: z.literal("merchant_product_performance_readiness"),
  status: z.enum(["ready", "blocked"]),
  status_label: z.string().default(""),
  joined_product_count: z.number(),
  merchant_sample_count: z.number(),
  ads_product_fact_count: z.number(),
  ga4_product_fact_count: z.number(),
  current_read_contracts: z.array(z.string()),
  required_read_contracts: z.array(z.string()),
  missing_read_contracts: z.array(z.string()),
  join_key_candidates: z.array(z.string()),
  sample_product_ids: z.array(z.string()),
  sample_product_summary_label: z.string().default(""),
  performance_rows: z.array(MerchantProductPerformanceRowSchema),
  source_connectors: z.array(z.string()),
  source_connector_labels: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  summary: z.string(),
  next_step: z.string(),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).default([])
});

export const MerchantPriceImpactReadinessSchema = z.object({
  id: z.literal("merchant_price_impact_readiness"),
  status: z.enum(["ready", "blocked"]),
  status_label: z.string().default(""),
  products_with_current_price: z.number(),
  products_with_previous_price: z.number(),
  products_with_price_change: z.number().default(0),
  products_with_unchanged_price_history: z.number().default(0),
  products_with_performance_metrics: z.number(),
  current_read_contracts: z.array(z.string()),
  required_read_contracts: z.array(z.string()),
  missing_read_contracts: z.array(z.string()),
  payload_preview: z.array(z.record(z.unknown())).default([]),
  preview_cards: z.array(ActionPreviewCardViewModelSchema).default([]),
  source_connectors: z.array(z.string()),
  source_connector_labels: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  summary: z.string(),
  next_step: z.string(),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).default([])
});

export const MerchantDiagnosticsResponseSchema = z.object({
  generated_at: z.string().nullable().optional(),
  language: z.literal("pl-PL"),
  strict_instruction: z.string(),
  connector: ConnectorStatusSchema,
  connector_status_label: z.string().default(""),
  latest_refresh: ConnectorRefreshRunSchema.nullable().optional(),
  latest_refresh_status_label: z.string().nullable().optional(),
  live_data_available: z.boolean(),
  live_data_status_label: z.string().default(""),
  product_count: z.number().nullable().optional(),
  issue_count: z.number().nullable().optional(),
  freshness_assessment: MerchantFreshnessAssessmentSchema,
  unknowns: z.array(MerchantUnknownFactSchema),
  product_sample_readiness: MerchantProductSampleReadinessSchema,
  product_performance_readiness: MerchantProductPerformanceReadinessSchema,
  price_impact_readiness: MerchantPriceImpactReadinessSchema,
  operator_summary: MerchantOperatorSummarySchema,
  issue_clusters: z.array(MerchantIssueClusterSchema),
  decision_queue: z.array(MerchantDecisionItemSchema),
  sections: z.array(MerchantDiagnosticSectionSchema),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  source_connector_labels: z.array(z.string()).default([]),
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
  blocked_claim_labels: z.array(z.string()).default([]),
  risk: z.enum(["low", "medium", "high", "critical"])
});

export const ContentDecisionItemSchema = z.object({
  id: z.string(),
  decision_type: z.enum([
    "block_until_vendor_read",
    "refresh_or_merge",
    "merge_create_after_inventory_check",
    "inventory_check_before_create",
    "block_as_tracking_not_content",
    "review_ahrefs_gap_records"
  ]),
  status: z.enum(["ready", "blocked"]),
  status_label: z.string().default(""),
  decision_type_label: z.string().default(""),
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
  wordpress_match_label: z.string().nullable().optional(),
  wordpress_match_confidence: z.string().nullable().optional(),
  wordpress_match_confidence_label: z.string().nullable().optional(),
  source_public_url: z.string().nullable().optional(),
  preview_url: z.string().nullable().optional(),
  intended_final_url: z.string().nullable().optional(),
  final_canonical_url: z.string().nullable().optional(),
  inventory_gate_status: z.string().nullable().optional(),
  inventory_gate_status_label: z.string().nullable().optional(),
  canonical_gate_status: z.string().nullable().optional(),
  canonical_gate_status_label: z.string().nullable().optional(),
  duplicate_gate_status: z.string().nullable().optional(),
  duplicate_gate_status_label: z.string().nullable().optional(),
  content_gate_summary: z.string().nullable().optional(),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  metric_facts: z.array(MetricFactSchema),
  ahrefs_candidate_rows: z
    .array(
      z.object({
        id: z.string(),
        topic: z.string(),
        gap_type: z.string(),
        gap_type_label: z.string().default(""),
        relevance_status: z.enum(["relevant", "review", "off_topic"]),
        relevance_status_label: z.string().default(""),
        relevance_score: z.number(),
        business_relevance_reasons: z.array(z.string()).default([]),
        business_relevance_reason_labels: z.array(z.string()).default([]),
        gsc_demand: z.enum(["present", "missing"]),
        gsc_demand_label: z.string().default(""),
        wordpress_inventory_match: z.enum(["present", "missing"]),
        wordpress_inventory_match_label: z.string().default(""),
        gsc_overlap_terms: z.array(z.string()).default([]),
        wordpress_overlap_urls: z.array(z.string()).default([]),
        keyword: z.string().nullable().optional(),
        competitor_domain: z.string().nullable().optional(),
        source_url: z.string().nullable().optional(),
        referenced_public_url: z.string().nullable().optional(),
        metric_name: z.string(),
        metric_value: z.union([z.string(), z.number()]),
        evidence_ids: z.array(z.string()),
        next_step: z.string()
      })
    )
    .default([]),
  action_ids: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).default([]),
  rationale: z.string(),
  next_step: z.string(),
  risk: z.enum(["low", "medium", "high", "critical"])
});

export const ContentOperatorSummarySchema = z.object({
  id: z.literal("content_operator_summary"),
  title: z.string(),
  summary: z.string(),
  next_step: z.string(),
  top_decision_ids: z.array(z.string()),
  confirmed_wordpress_count: z.number(),
  missing_wordpress_count: z.number(),
  current_site_match_count: z.number(),
  decision_type_labels: z.array(z.string()),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  action_ids: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).default([])
});

export const ContentMarketerDecisionSchema = z.object({
  id: z.string(),
  technical_decision_id: z.string(),
  status: z.enum(["ready", "blocked"]),
  decision: z.string(),
  mode_label: z.string(),
  why_it_matters: z.string(),
  safe_next_action: z.string(),
  metric_tiles: z.record(z.union([z.string(), z.number()])).default({}),
  content_angle: z.string().nullable().optional(),
  h1_direction: z.string().nullable().optional(),
  h2_direction: z.array(z.string()).default([]),
  faq_direction: z.array(z.string()).default([]),
  cta_direction: z.string().nullable().optional(),
  source_facts: z.array(z.string()).default([]),
  blocked_claims: z.array(z.string()).default([]),
  missing_inputs: z.array(z.string()).default([]),
  evidence_summary: z.string(),
  source_connectors: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()).default([]),
  measurement_plan: z.string(),
  source_public_url: z.string().nullable().optional(),
  preview_url: z.string().nullable().optional(),
  intended_final_url: z.string().nullable().optional(),
  final_canonical_url: z.string().nullable().optional()
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
  operator_summary: ContentOperatorSummarySchema,
  marketer_decision: ContentMarketerDecisionSchema.nullable().optional(),
  decision_queue: z.array(ContentDecisionItemSchema),
  sections: z.array(ContentDiagnosticSectionSchema),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  source_connector_labels: z.array(z.string()).default([]),
  action_ids: z.array(z.string()),
  blocker_count: z.number()
});

export const ContentPreflightItemSchema = z.object({
  id: z.string(),
  technical_decision_id: z.string(),
  recommended_mode: z.enum(["preserve", "refresh", "merge", "create", "block"]),
  recommended_mode_label: z.string().default(""),
  status: z.enum(["allowed", "review_required", "blocked"]),
  status_label: z.string().default(""),
  create_allowed: z.boolean(),
  draft_allowed: z.boolean(),
  wordpress_draft_allowed: z.boolean(),
  sales_brief_allowed: z.boolean(),
  source_public_url: z.string().nullable().optional(),
  preview_url: z.string().nullable().optional(),
  intended_final_url: z.string().nullable().optional(),
  final_canonical_url: z.string().nullable().optional(),
  inventory_gate_status: z.string().nullable().optional(),
  inventory_gate_status_label: z.string().nullable().optional(),
  canonical_gate_status: z.string().nullable().optional(),
  canonical_gate_status_label: z.string().nullable().optional(),
  duplicate_gate_status: z.string().nullable().optional(),
  duplicate_gate_status_label: z.string().nullable().optional(),
  claim_gate_status: z.string(),
  claim_gate_status_label: z.string().default(""),
  service_fit_status: z.string(),
  service_fit_status_label: z.string().default(""),
  similar_existing_urls: z.array(z.string()),
  query_overlap_summary: z.string(),
  blocked_claims: z.array(z.string()),
  missing_inputs: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  source_connectors: z.array(z.string()),
  next_step: z.string()
});

export const ContentPreflightResponseSchema = z.object({
  generated_at: z.string().nullable().optional(),
  language: z.literal("pl-PL"),
  strict_instruction: z.string(),
  primary_item: ContentPreflightItemSchema.nullable().optional(),
  items: z.array(ContentPreflightItemSchema),
  evidence_ids: z.array(z.string()),
  source_connectors: z.array(z.string()),
  blocker_count: z.number()
});

export const Ga4DiagnosticSectionSchema = z.object({
  id: z.string(),
  label: z.string().default(""),
  title: z.string(),
  status: z.enum(["ready", "blocked", "missing"]),
  status_label: z.string().default(""),
  summary: z.string(),
  diagnosis: z.string(),
  next_step: z.string(),
  source_connectors: z.array(z.string()),
  source_connector_labels: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  metric_facts: z.array(MetricFactSchema),
  tactical_items: z.array(TacticalQueueItemSchema),
  action_ids: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).default([]),
  risk: z.enum(["low", "medium", "high", "critical"]),
  risk_label: z.string().default("")
});

export const Ga4DecisionItemSchema = z.object({
  id: z.string(),
  decision_type: z.enum([
    "fix_measurement",
    "review_traffic_quality",
    "review_landing_mapping"
  ]),
  decision_type_label: z.string().default(""),
  title: z.string(),
  status: z.enum(["ready", "blocked"]),
  status_label: z.string().default(""),
  priority: z.number(),
  metric_tiles: z.record(z.union([z.string(), z.number()])),
  landing_page: z.string().nullable().optional(),
  landing_page_label: z.string().default(""),
  source_medium: z.string().nullable().optional(),
  source_medium_label: z.string().default(""),
  campaign_name: z.string().nullable().optional(),
  campaign_name_label: z.string().default(""),
  wordpress_match: z.string().nullable().optional(),
  wordpress_match_label: z.string().nullable().optional(),
  wordpress_match_confidence: z.string().nullable().optional(),
  wordpress_match_confidence_label: z.string().nullable().optional(),
  wordpress_content_url: z.string().nullable().optional(),
  source_connectors: z.array(z.string()),
  source_connector_labels: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  metric_facts: z.array(MetricFactSchema),
  action_ids: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).default([]),
  rationale: z.string(),
  next_step: z.string(),
  risk: z.enum(["low", "medium", "high", "critical"]),
  risk_label: z.string().default("")
});

export const Ga4ConversionReadinessContractSchema = z.object({
  id: z.literal("ga4_conversion_readiness_contract"),
  status: z.enum(["ready", "blocked"]),
  status_label: z.string().default(""),
  title: z.string(),
  summary: z.string(),
  allowed_metrics: z.array(z.string()),
  available_read_contracts: z.array(z.string()),
  available_read_contract_labels: z.array(z.string()).optional().default([]),
  missing_read_contracts: z.array(z.string()),
  missing_read_contract_labels: z.array(z.string()).optional().default([]),
  conversion_like_metric_count: z.number(),
  dimensioned_behavior_metric_count: z.number(),
  landing_group_count: z.number(),
  source_connectors: z.array(z.string()),
  source_connector_labels: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  action_ids: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  next_step: z.string(),
  risk: z.enum(["low", "medium", "high", "critical"])
});

export const Ga4FreshnessAssessmentSchema = z.object({
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

export const Ga4OperatorSummarySchema = z.object({
  id: z.literal("ga4_operator_summary"),
  title: z.string(),
  summary: z.string(),
  next_step: z.string(),
  top_decision_ids: z.array(z.string()),
  measurement_issue_count: z.number(),
  wordpress_missing_count: z.number(),
  conversion_readiness_status: z.enum(["ready", "blocked"]),
  source_connectors: z.array(z.string()),
  source_connector_labels: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  action_ids: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).default([])
});

export const Ga4DiagnosticsResponseSchema = z.object({
  generated_at: z.string().nullable().optional(),
  language: z.literal("pl-PL"),
  strict_instruction: z.string(),
  connector: ConnectorStatusSchema,
  connector_status_label: z.string().default(""),
  latest_refresh: ConnectorRefreshRunSchema.nullable().optional(),
  latest_refresh_status_label: z.string().default(""),
  live_data_available: z.boolean(),
  live_data_status_label: z.string().default(""),
  landing_group_count: z.number(),
  low_engagement_count: z.number(),
  wordpress_match_count: z.number(),
  freshness_assessment: Ga4FreshnessAssessmentSchema,
  conversion_readiness_contract: Ga4ConversionReadinessContractSchema,
  operator_summary: Ga4OperatorSummarySchema,
  decision_queue: z.array(Ga4DecisionItemSchema),
  sections: z.array(Ga4DiagnosticSectionSchema),
  evidence_ids: z.array(z.string()),
  action_ids: z.array(z.string()),
  blocker_count: z.number(),
  decision_blocker_count: z.number()
});

export const LocaloAccessProbeSchema = z.object({
  status: z.enum(["access_ready", "access_blocked", "unknown"]),
  status_label: z.string().default(""),
  source_run_id: z.string().nullable().optional(),
  mcp_initialize_status: z.number().nullable().optional(),
  access_check_label: z.string().default(""),
  authorization_code_supported: z.boolean().nullable().optional(),
  authorization_code_supported_label: z.string().default(""),
  authorization_readiness_label: z.string().default(""),
  pkce_s256_supported: z.boolean().nullable().optional(),
  pkce_s256_supported_label: z.string().default(""),
  secure_readiness_label: z.string().default(""),
  access_token_present: z.boolean().nullable().optional(),
  access_token_present_label: z.string().default(""),
  credential_readiness_label: z.string().default(""),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  summary: z.string()
});

export const LocaloDiagnosticSectionSchema = z.object({
  id: z.string(),
  title: z.string(),
  status: z.enum(["ready", "blocked", "missing"]),
  status_label: z.string().default(""),
  summary: z.string(),
  diagnosis: z.string(),
  next_step: z.string(),
  source_connectors: z.array(z.string()),
  source_connector_labels: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  metric_facts: z.array(MetricFactSchema),
  action_ids: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).default([]),
  risk: z.enum(["low", "medium", "high", "critical"])
});

export const LocaloReadContractStatusSchema = z.object({
  id: z.enum([
    "place_inventory",
    "local_rankings",
    "gbp_visibility",
    "competitor_visibility",
    "reviews",
    "local_tasks"
  ]),
  id_label: z.string().default(""),
  status: z.enum(["ready", "missing"]),
  status_label: z.string().default(""),
  evidence_kind: z.string(),
  metric_fact_names: z.array(z.string()).default([]),
  metric_fact_labels: z.record(z.string()).default({}),
  blocked_claims: z.array(z.string()).default([]),
  blocked_claim_labels: z.array(z.string()).default([]),
  next_step: z.string()
});

export const LocaloDecisionItemSchema = z.object({
  id: z.string(),
  decision_type: z.enum([
    "access_ready_wait_for_visibility_facts",
    "fix_access",
    "review_local_visibility",
    "block_visibility_claims"
  ]),
  decision_type_label: z.string().default(""),
  status: z.enum(["ready", "blocked"]),
  status_label: z.string().default(""),
  title: z.string(),
  summary: z.string(),
  rationale: z.string(),
  next_step: z.string(),
  access_status: z.enum(["access_ready", "access_blocked", "unknown"]),
  access_status_label: z.string().default(""),
  priority: z.number(),
  priority_label: z.string().default(""),
  metric_tiles: z.record(z.union([z.string(), z.number()])).default({}),
  allowed_evidence: z.array(z.string()),
  allowed_evidence_labels: z.array(z.string()).default([]),
  missing_read_contracts: z.array(z.string()),
  missing_read_contract_labels: z.array(z.string()).default([]),
  read_contract_statuses: z.array(LocaloReadContractStatusSchema).default([]),
  source_connectors: z.array(z.string()),
  source_connector_labels: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  metric_facts: z.array(MetricFactSchema),
  metric_fact_labels: z.record(z.string()).default({}),
  action_ids: z.array(z.string()),
  knowledge_card_ids: z.array(z.string()).default([]),
  expert_rule_ids: z.array(z.string()).default([]),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).default([]),
  risk: z.enum(["low", "medium", "high", "critical"])
});

export const LocaloOperatorSummarySchema = z.object({
  id: z.literal("localo_operator_summary"),
  title: z.string(),
  summary: z.string(),
  next_step: z.string(),
  top_decision_ids: z.array(z.string()),
  access_status: z.enum(["access_ready", "access_blocked", "unknown"]),
  access_status_label: z.string().default(""),
  visibility_fact_count: z.number(),
  missing_read_contracts: z.array(z.string()),
  missing_read_contract_labels: z.array(z.string()).default([]),
  read_contract_statuses: z.array(LocaloReadContractStatusSchema).default([]),
  source_connectors: z.array(z.string()),
  source_connector_labels: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  action_ids: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).default([])
});

export const LocaloDiagnosticsResponseSchema = z.object({
  generated_at: z.string().nullable().optional(),
  language: z.literal("pl-PL"),
  strict_instruction: z.string(),
  connector: ConnectorStatusSchema,
  connector_status_label: z.string().default(""),
  latest_refresh: ConnectorRefreshRunSchema.nullable().optional(),
  latest_refresh_status_label: z.string().nullable().optional(),
  access_probe: LocaloAccessProbeSchema,
  live_data_available: z.boolean(),
  visibility_fact_count: z.number(),
  read_contract_statuses: z.array(LocaloReadContractStatusSchema).default([]),
  operator_summary: LocaloOperatorSummarySchema,
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
  status_label: z.string().default(""),
  summary: z.string(),
  diagnosis: z.string(),
  next_step: z.string(),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  metric_facts: z.array(MetricFactSchema),
  metric_fact_labels: z.record(z.string()).default({}),
  action_ids: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).default([]),
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
  status_label: z.string().default(""),
  decision_type_label: z.string().default(""),
  title: z.string(),
  summary: z.string(),
  rationale: z.string(),
  next_step: z.string(),
  priority: z.number(),
  priority_label: z.string().default(""),
  metric_tiles: z.record(z.union([z.string(), z.number()])).default({}),
  allowed_evidence: z.array(z.string()),
  allowed_evidence_labels: z.array(z.string()).default([]),
  missing_read_contracts: z.array(z.string()),
  missing_read_contract_labels: z.array(z.string()).default([]),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  metric_facts: z.array(MetricFactSchema),
  metric_fact_labels: z.record(z.string()).default({}),
  action_ids: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).default([]),
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
  gap_type_label: z.string().default(""),
  title: z.string(),
  summary: z.string(),
  source_url: z.string().nullable().optional(),
  referenced_public_url: z.string().nullable().optional(),
  competitor_domain: z.string().nullable().optional(),
  keyword: z.string().nullable().optional(),
  metric_facts: z.array(MetricFactSchema),
  metric_fact_labels: z.record(z.string()).default({}),
  evidence_ids: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  next_step: z.string(),
  risk: z.enum(["low", "medium", "high", "critical"])
});

export const AhrefsGapReadContractSchema = z.object({
  id: z.literal("ahrefs_gap_read_contract"),
  status: z.enum(["ready", "blocked"]),
  status_label: z.string().default(""),
  title: z.string(),
  summary: z.string(),
  available_read_contracts: z.array(z.string()),
  available_read_contract_labels: z.array(z.string()).default([]),
  missing_read_contracts: z.array(z.string()),
  missing_read_contract_labels: z.array(z.string()).default([]),
  allowed_evidence: z.array(z.string()),
  allowed_evidence_labels: z.array(z.string()).default([]),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).default([]),
  operator_review_gates: z.array(z.string()),
  operator_review_gate_labels: z.array(z.string()).default([]),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  gap_records: z.array(AhrefsGapRecordSchema),
  gap_record_count: z.number(),
  next_step: z.string(),
  risk: z.enum(["low", "medium", "high", "critical"])
});

export const AhrefsOperatorSummarySchema = z.object({
  id: z.literal("ahrefs_operator_summary"),
  title: z.string(),
  summary: z.string(),
  next_step: z.string(),
  top_decision_ids: z.array(z.string()),
  gap_read_status: z.enum(["ready", "blocked"]),
  gap_read_status_label: z.string().default(""),
  authority_fact_count: z.number(),
  gap_fact_count: z.number(),
  available_read_contracts: z.array(z.string()),
  available_read_contract_labels: z.array(z.string()).default([]),
  missing_read_contracts: z.array(z.string()),
  missing_read_contract_labels: z.array(z.string()).default([]),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  action_ids: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).default([])
});

export const AhrefsDiagnosticsResponseSchema = z.object({
  generated_at: z.string().nullable().optional(),
  language: z.literal("pl-PL"),
  strict_instruction: z.string(),
  connector: ConnectorStatusSchema,
  connector_status_label: z.string().default(""),
  latest_refresh: ConnectorRefreshRunSchema.nullable().optional(),
  latest_refresh_status_label: z.string().nullable().optional(),
  live_data_status_label: z.string().default(""),
  live_data_available: z.boolean(),
  authority_fact_count: z.number(),
  gap_fact_count: z.number(),
  gap_read_contract: AhrefsGapReadContractSchema,
  operator_summary: AhrefsOperatorSummarySchema,
  decision_queue: z.array(AhrefsDecisionItemSchema),
  sections: z.array(AhrefsDiagnosticSectionSchema),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  source_connector_labels: z.array(z.string()).default([]),
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
  card_type_label: z.string().default(""),
  title: z.string(),
  display_title: z.string().default(""),
  summary: z.string(),
  source_type: z.string(),
  source_type_label: z.string().default(""),
  source_id: z.string(),
  source_url_or_path: z.string(),
  extracted_at: z.string(),
  confidence: z.number(),
  last_seen_at: z.string(),
  source_lineage: z.array(z.string()),
  source_lineage_summary_label: z.string().default("")
});

export const MarketingPlaybookSchema = z.object({
  id: z.string(),
  family: z.string(),
  title: z.string(),
  display_title: z.string().default(""),
  card_type: z.string(),
  card_type_label: z.string().default(""),
  source_type_label: z.string().default(""),
  source_anchors: z.array(z.string()).min(1),
  required_evidence: z.array(z.string()).min(1),
  maps_to_opportunity_types: z.array(z.string()).min(1),
  maps_to_action_types: z.array(z.string()).min(1),
  expert_rule_ids: z.array(z.string()),
  compact_playbook: z.string(),
  refusal_rules: z.array(z.string()),
  output_contract: z.string(),
  source_path: z.string(),
  required_evidence_summary_label: z.string().default(""),
  mapped_action_type_summary_label: z.string().default("")
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
  status_label: z.string().default(""),
  route: z.string(),
  route_label: z.string().default(""),
  skill_id: z.string().nullable().optional(),
  summary: z.string(),
  next_step: z.string(),
  source_connectors: z.array(z.string()),
  source_connector_labels: z.array(z.string()).default([]),
  source_connector_summary_label: z.string().default(""),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  action_ids: z.array(z.string()),
  action_summary_label: z.string().default(""),
  metric_tiles: z.record(z.union([z.string(), z.number()])),
  knowledge_card_ids: z.array(z.string()),
  playbook_ids: z.array(z.string()),
  expert_rule_ids: z.array(z.string()),
  knowledge_summary_label: z.string().default(""),
  required_evidence: z.array(z.string()),
  required_evidence_summary_label: z.string().default(""),
  missing_contracts: z.array(z.string()),
  missing_contract_labels: z.array(z.string()).default([]),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).default([]),
  source_lineage: z.array(z.string()),
  source_lineage_summary_label: z.string().default(""),
  risk: z.enum(["low", "medium", "high"]),
  risk_label: z.string().default("")
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
  domain: z.string().default("wilq"),
  freshness: FreshnessStateSchema.default({ state: "unknown" }),
  freshness_label: z.string().default(""),
  decision_state: DecisionStateSchema.default("unknown"),
  decision_state_label: z.string().default(""),
  route: z.string(),
  route_label: z.string().default(""),
  cta_label: z.string().default(""),
  status: z.enum(["ready", "blocked"]),
  priority: z.number(),
  priority_label: z.string().default(""),
  metric_tiles: z.record(z.union([z.string(), z.number()])),
  metric_facts: z.array(MetricFactSchema).default([]),
  co_widzimy: z.string(),
  dlaczego_to_ma_znaczenie: z.string(),
  bezpieczny_next_step: z.string(),
  why_it_matters: z.string(),
  operator_action: z.string(),
  source_connectors: z.array(z.string()),
  source_connector_labels: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()),
  evidence_summary: z.string().default(""),
  action_ids: z.array(z.string()),
  action_summary: z.string().default(""),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).default([]),
  skill_id: z.string().nullable().optional(),
  skill_label: z.string().nullable().optional(),
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
  status_label: z.string().nullable().optional(),
  route: z.string().nullable().optional(),
  route_label: z.string().nullable().optional(),
  skill_id: z.string().nullable().optional(),
  safe_next_step: z.string().nullable().optional(),
  source_connectors: z.array(z.string()).default([]),
  source_connector_labels: z.array(z.string()).default([]),
  source_connector_summary_label: z.string().default(""),
  evidence_ids: z.array(z.string()).default([]),
  evidence_summary_label: z.string().default(""),
  action_ids: z.array(z.string()).default([]),
  action_summary_label: z.string().default(""),
  blocked_claims: z.array(z.string()).default([]),
  blocked_claim_labels: z.array(z.string()).default([]),
  blocked_claim_summary_label: z.string().default(""),
  metric_tiles: z.record(z.union([z.string(), z.number()])).default({}),
  missing_contracts: z.array(z.string()).default([]),
  missing_contract_labels: z.array(z.string()).default([]),
  missing_contract_summary_label: z.string().default(""),
  risk: z.enum(["low", "medium", "high"]).default("low"),
  risk_label: z.string().nullable().optional()
});

export const DemandGenReadinessContractSchema = z.object({
  status: z.enum(["ready", "blocked"]),
  status_label: z.string().default(""),
  title: z.string(),
  summary: z.string(),
  metric_tiles: z.record(z.union([z.string(), z.number()])).default({}),
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
  payload_preview: z.array(z.record(z.unknown())).default([]),
  preview_cards: z.array(ActionPreviewCardViewModelSchema).default([]),
  campaign_rows_evaluated: z.number(),
  campaign_channel_counts: z.record(z.number()),
  campaign_channel_labels: z.record(z.string()).optional().default({}),
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
    evidence_ids: z.array(z.string()).default([])
  })).default([]),
  demand_gen_creative_asset_rows: z.array(z.object({
    asset_id: z.string().nullable().optional(),
    asset_type: z.string().nullable().optional(),
    field_type: z.string().nullable().optional(),
    impressions: z.number().nullable().optional(),
    evidence_ids: z.array(z.string()).default([])
  })).default([]),
  demand_gen_landing_quality_rows: z.array(z.object({
    campaign_id: z.string().nullable().optional(),
    campaign_name: z.string(),
    landing_page: z.string(),
    source_medium: z.string().nullable().optional(),
    active_users: z.number().nullable().optional(),
    sessions: z.number().nullable().optional(),
    engagement_rate: z.number().nullable().optional(),
    evidence_ids: z.array(z.string()).default([])
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
    evidence_ids: z.array(z.string()).default([])
  })).default([]),
  next_step: z.string(),
  risk: z.enum(["low", "medium", "high"]),
  risk_label: z.string().default("")
});

export const WorkflowInputSchema = z.object({
  connector_ids: z.array(z.string()),
  parameters: z.record(z.unknown())
});

export const WorkflowOutputSchema = z.object({
  evidence_ids: z.array(z.string()),
  action_ids: z.array(z.string()),
  errors: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  action_summary_label: z.string().default(""),
  error_summary_label: z.string().default("")
});

export const WorkflowRunSchema = z.object({
  id: z.string(),
  workflow_id: z.string(),
  status: z.enum(["queued", "running", "completed", "failed", "blocked"]),
  status_label: z.string().default(""),
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
  content_preflight: ContentPreflightResponseSchema.optional(),
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
export type ActionPreviewCardViewModel = z.infer<typeof ActionPreviewCardViewModelSchema>;
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
export type AdsSharedBudgetDistributionRow = z.infer<
  typeof AdsSharedBudgetDistributionRowSchema
>;
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
export type ContentPreflightResponse = z.infer<typeof ContentPreflightResponseSchema>;
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
