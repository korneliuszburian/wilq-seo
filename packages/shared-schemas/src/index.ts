import { z } from "zod";

import {
  ContentDraftPackageSchema,
  ContentWordPressDraftHandoffSchema
} from "./contentWorkflow";
import {
  ContentDiagnosticSectionSchema,
  ContentDiagnosticsResponseSchema,
} from "./content_diagnostics";
import {
  ContentPreflightResponseSchema
} from "./content_preflight";
import {
  ConnectorRefreshRunSchema,
  ConnectorStatusSchema,
  ConnectorSummarySchema,
  EvidenceSchema,
  FreshnessStateSchema
  ,MetricFactSchema
} from "./connectors";
import {
  ActionObjectSchema,
  ActionPreviewCardViewModelSchema
} from "./actions";
import {
  MarketingBriefSchema,
  TacticalQueueResponseSchema
} from "./marketing";
import {
  AdsAccountCurrencyReadContractSchema,
  AdsBudgetPacingReadContractSchema,
  AdsBudgetPacingRowSchema,
  AdsCampaignMetricRowSchema,
  AdsDiagnosticSectionSchema,
  AdsSharedBudgetDistributionRowSchema,
} from "./ads_campaigns";
import {
  AdsKeywordMatchContextRowSchema,
  AdsKeywordMatchContextReadContractSchema
} from "./ads_keyword_contracts";
import {
  AdsCustomSegmentCandidateSchema,
  AdsCustomSegmentsReadContractSchema
} from "./ads_custom_segments";
import {
  AdsNegativeKeywordCandidateSchema,
  AdsNegativeKeywordPayloadPreviewSchema,
  AdsNegativeKeywordsReadContractSchema
} from "./ads_negative_keywords";
import { AdsDiagnosticsResponseSchema } from "./ads_diagnostics";
import {
  Ga4DecisionItemSchema,
  Ga4DiagnosticsResponseSchema,
  Ga4DiagnosticSectionSchema
} from "./ga4_diagnostics";
import {
  LocaloAccessProbeSchema,
  LocaloDecisionItemSchema,
  LocaloDiagnosticsResponseSchema,
  LocaloDiagnosticSectionSchema
} from "./localo_diagnostics";
import {
  AhrefsDecisionItemSchema,
  AhrefsDiagnosticsResponseSchema,
  AhrefsDiagnosticSectionSchema
} from "./ahrefs_diagnostics";
import {
  ExpertCapabilitySchema,
  ExpertRuleSchema,
  ExpertRuleSummarySchema
} from "./expert_contracts";
import {
  ExpertKnowledgeSourceSchema,
  KnowledgeCardSchema,
  KnowledgeCompilerResultSchema,
  KnowledgeDecisionBindingSchema,
  KnowledgeOperatingMapResponseSchema,
  KnowledgeTaxonomyEntrySchema,
  KnowledgeTaxonomyTypeSchema,
  MarketingPlaybookSchema
} from "./knowledge_contracts";
import {
  MerchantDecisionItemSchema,
  MerchantDiagnosticSectionSchema,
  MerchantDiagnosticsResponseSchema
} from "./merchant_diagnostics";

export * from "./contentWorkflow";
export * from "./content_diagnostics";
export * from "./content_preflight";
export * from "./connectors";
export * from "./actions";
export * from "./marketing";
export * from "./ads_campaigns";
export * from "./ads_keyword_contracts";
export * from "./ads_keyword_planner_contracts";
export * from "./ads_custom_segments";
export * from "./ads_review_contracts";
export * from "./ads_search_terms";
export * from "./ads_negative_keywords";
export * from "./ads_change_history";
export * from "./ads_decisions";
export * from "./ads_diagnostics";
export * from "./ga4_diagnostics";
export * from "./localo_diagnostics";
export * from "./ahrefs_diagnostics";
export * from "./expert_contracts";
export * from "./knowledge_contracts";
export * from "./merchant_diagnostics";

export const DecisionStateSchema = z.enum(["ready", "stale", "blocked", "missing", "unknown"]);

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
  metric_tiles: z.record(z.string(), z.union([z.string(), z.number()])).default({}),
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
  metric_tiles: z.record(z.string(), z.union([z.string(), z.number()])),
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
  metric_tiles: z.record(z.string(), z.union([z.string(), z.number()])),
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

export const WorkOrderStatusSchema = z.enum(["review_required", "blocked", "done"]);
export const WorkOrderOwnerRoleSchema = z.enum([
  "marketer",
  "ads_analytics",
  "content_seo",
  "product_feed",
  "local_seo",
  "owner_review",
  "developer_audit"
]);

export const WorkOrderSchema = z.object({
  id: z.string(),
  title: z.string(),
  status: WorkOrderStatusSchema,
  status_label: z.string().default(""),
  owner_role: WorkOrderOwnerRoleSchema,
  priority: z.number(),
  domain: z.string().default("wilq"),
  route: z.string(),
  route_label: z.string().default(""),
  summary: z.string(),
  why_it_matters: z.string(),
  next_safe_step: z.string(),
  close_condition: z.string(),
  source_connectors: z.array(z.string()).default([]),
  source_connector_labels: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()).default([]),
  evidence_summary: z.string().default(""),
  action_ids: z.array(z.string()).default([]),
  action_summary: z.string().default(""),
  blocked_claims: z.array(z.string()).default([]),
  blocked_claim_labels: z.array(z.string()).default([]),
  freshness: FreshnessStateSchema.default({ state: "unknown" }),
  freshness_label: z.string().default(""),
  risk: z.enum(["low", "medium", "high", "critical"]).default("medium"),
  decision_id: z.string().nullable().optional()
});

export const DailyCheckConnectorRefSchema = z.object({
  connector_id: z.string(),
  status: z.enum(["checked", "skipped"]),
  freshness: FreshnessStateSchema.default({ state: "unknown" }),
  reason: z.string().default("")
});

export const DailyCheckItemCategorySchema = z.enum([
  "anomaly",
  "risk",
  "opportunity",
  "blocked_recommendation",
  "safe_next_action",
  "do_not_touch"
]);

export const DailyCheckItemSchema = z.object({
  id: z.string(),
  category: DailyCheckItemCategorySchema,
  title: z.string(),
  status: z.enum(["ready", "review_required", "blocked"]),
  priority: z.number(),
  summary: z.string(),
  next_step: z.string(),
  source_connectors: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()).default([]),
  expert_rule_ids: z.array(z.string()).default([]),
  freshness: FreshnessStateSchema.default({ state: "unknown" }),
  action_ids: z.array(z.string()).default([]),
  blocked_claims: z.array(z.string()).default([]),
  missing_contracts: z.array(z.string()).default([]),
  risk: z.enum(["low", "medium", "high", "critical"]).default("medium")
}).superRefine((item, ctx) => {
  if (item.status === "blocked" || item.category === "blocked_recommendation") return;
  const missing: string[] = [];
  if (item.source_connectors.length === 0) missing.push("source_connectors");
  if (item.evidence_ids.length === 0) missing.push("evidence_ids");
  if (item.expert_rule_ids.length === 0) missing.push("expert_rule_ids");
  if (item.freshness.state === "unknown" || item.freshness.state === "missing") {
    missing.push("freshness");
  }
  if (missing.length > 0) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: `Daily check item ${item.id} lacks required trace fields: ${missing.join(", ")}`
    });
  }
});

export const DailyCheckResultSchema = z.object({
  workspace_id: z.string(),
  date: z.string(),
  status: z.enum(["ready", "review_ready", "blocked", "degraded"]),
  checked_connectors: z.array(DailyCheckConnectorRefSchema).default([]),
  skipped_connectors: z.array(DailyCheckConnectorRefSchema).default([]),
  anomalies: z.array(DailyCheckItemSchema).default([]),
  risks: z.array(DailyCheckItemSchema).default([]),
  opportunities: z.array(DailyCheckItemSchema).default([]),
  blocked_recommendations: z.array(DailyCheckItemSchema).default([]),
  safe_next_actions: z.array(DailyCheckItemSchema).default([]),
  do_not_touch: z.array(DailyCheckItemSchema).default([]),
  evidence_ids: z.array(z.string()).default([]),
  source_connectors: z.array(z.string()).default([]),
  expert_rules_used: z.array(z.string()).default([]),
  freshness: FreshnessStateSchema.default({ state: "unknown" })
});

export const CommandCenterResponseSchema = z.object({
  generated_at: z.string().nullable().optional(),
  strict_instruction: z.string(),
  primary_next_step: z.string(),
  blocker_count: z.number(),
  tactical_item_count: z.number(),
  source_connectors: z.array(z.string()).default([]),
  source_connector_labels: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()).default([]),
  evidence_summary: z.string().default(""),
  action_ids: z.array(z.string()).default([]),
  action_summary: z.string().default(""),
  daily_decisions: z.array(DailyDecisionSchema),
  work_orders: z.array(WorkOrderSchema).default([]),
  operator_brief: z.array(CommandCenterBriefItemSchema),
  demo_script: z.array(CommandCenterDemoStepSchema),
  action_plan: z.array(CommandCenterActionPlanItemSchema),
  connector_summary: ConnectorSummarySchema,
  sections: z.record(z.string(), z.array(OpportunitySchema)),
  active_actions: z.array(ActionObjectSchema),
  connector_health: z.array(ConnectorStatusSchema),
  codex_operator_status: z.record(z.string(), z.unknown())
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
  metric_tiles: z.record(z.string(), z.union([z.string(), z.number()])).default({}),
  missing_contracts: z.array(z.string()).default([]),
  missing_contract_labels: z.array(z.string()).default([]),
  missing_contract_summary_label: z.string().default(""),
  missing_contract_detail_label: z.string().default(""),
  risk: z.enum(["low", "medium", "high"]).default("low"),
  risk_label: z.string().nullable().optional()
});

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

export const WorkflowInputSchema = z.object({
  connector_ids: z.array(z.string()),
  parameters: z.record(z.string(), z.unknown())
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

export const SocialHistoryInventorySourceSchema = z.object({
  channel: z.enum(["linkedin", "facebook"]),
  connector_id: z.enum(["linkedin", "facebook"]),
  inventory_status: z.enum(["missing", "review_ready"]),
  connector_access_status: z.enum(["configured", "missing_credentials", "unavailable"]),
  required_evidence_id: z.string(),
  required_metadata_fields: z.array(z.string()),
  safe_collection_mode: z.literal("metadata_only"),
  raw_post_body_allowed: z.literal(false)
});

export const SocialHistoryDiscoverySeedSchema = z.object({
  id: z.string(),
  channel: z.enum(["linkedin", "facebook"]),
  source_type: z.literal("public_posts_url"),
  source_url: z.string(),
  status: z.literal("seeded_not_collected"),
  safe_collection_mode: z.literal("metadata_only"),
  raw_post_body_allowed: z.literal(false),
  required_review: z.literal(true),
  operator_note: z.string()
});

export const SocialHistoryInventorySchema = z.object({
  contract: z.literal("social_history_inventory_v1"),
  read_only: z.literal(true),
  status: z.enum(["missing", "invalid", "review_ready"]),
  status_label: z.string(),
  duplicate_risk_status: z.literal("blocked_until_social_history_review"),
  required_sources: z.array(z.enum(["linkedin", "facebook"])),
  missing_evidence_ids: z.array(z.string()),
  metadata_source_configured: z.boolean(),
  metadata_source_status: z.enum(["not_configured", "invalid", "review_ready"]),
  item_count: z.number(),
  channel_counts: z.record(z.string(), z.number()),
  import_errors: z.array(z.string()),
  sources: z.array(SocialHistoryInventorySourceSchema),
  discovery_seeds: z.array(SocialHistoryDiscoverySeedSchema),
  input_template: z.object({
    contract: z.literal("social_history_inventory_v1"),
    collected_at: z.string(),
    reviewer: z.string(),
    items: z.array(z.object({
      channel: z.enum(["linkedin", "facebook"]),
      published_at: z.string(),
      topic: z.string(),
      service: z.string(),
      claim: z.string(),
      cta: z.string(),
      format: z.string(),
      post_url_or_id: z.string(),
      source_evidence_id: z.string()
    })),
    _instruction: z.string()
  }),
  allowed_uses: z.array(z.string()),
  blocked_uses: z.array(z.string()),
  dedupe_requirements: z.array(z.string()),
  operator_next_step: z.string()
});

export const SocialHistoryImportAuditSchema = z.object({
  contract: z.literal("social_history_inventory_v1"),
  read_only: z.literal(true),
  status: z.enum(["invalid", "review_ready"]),
  item_count: z.number(),
  channel_counts: z.record(z.string(), z.number()),
  missing_required_sources: z.array(z.enum(["linkedin", "facebook"])),
  required_metadata_fields: z.array(z.string()),
  forbidden_metadata_fields: z.array(z.string()),
  errors: z.array(z.string()),
  duplicate_free_claim_allowed: z.literal(false),
  publish_allowed: z.literal(false),
  operator_next_step: z.string()
});

const WordPressAuthoringReadinessSchema = z.enum([
  "available",
  "configured",
  "not_configured",
  "missing",
  "blocked",
  "unknown"
]);

const WordPressAuthoringDiscoveryMethodSchema = z.enum([
  "rest",
  "acf_rest",
  "acf_export",
  "wp_cli",
  "helper",
  "env_config"
]);

const WordPressAuthoringBlockerSchema = z.object({
  code: z.string(),
  label: z.string(),
  reason: z.string(),
  next_step: z.string(),
  source_ref: z.string().nullable().optional()
});

const WordPressAuthoringDevSectionSchema = z.object({
  section_index: z.number(),
  acf_field_name: z.string(),
  layout_name: z.string(),
  layout_label: z.string(),
  title: z.string().default(""),
  text_summary: z.string().default(""),
  field_names: z.array(z.string()).default([]),
  text_field_paths: z.array(z.string()).default([])
});

const WordPressAuthoringDevPageSchema = z.object({
  post_id: z.string(),
  slug: z.string(),
  title: z.string(),
  link: z.string(),
  status: z.string(),
  modified: z.string(),
  modified_gmt: z.string(),
  template: z.string().default(""),
  parent: z.string().default(""),
  acf_field_name: z.string().nullable().optional(),
  section_count: z.number().default(0),
  sections: z.array(WordPressAuthoringDevSectionSchema).default([])
});

export const WordPressAuthoringProfileSchema = z.object({
  profile_version: z.literal("wordpress_authoring_profile_v1"),
  connector: z.string(),
  site_kind: z.string(),
  authoring_target: z.string(),
  discovery_mode: z.string(),
  discovery_order: z.array(WordPressAuthoringDiscoveryMethodSchema),
  rest_api: z.object({
    method: z.literal("rest"),
    status: WordPressAuthoringReadinessSchema,
    base_url_configured: z.boolean(),
    auth_configured: z.boolean(),
    public_url_configured: z.boolean(),
    post_types: z.array(z.string())
  }),
  acf: z.object({
    enabled_state: z.enum(["enabled", "disabled", "unknown"]),
    rest_enabled_state: z.enum(["enabled", "disabled", "unknown"]),
    flexible_content_field_name: z.string().nullable().optional(),
    post_types: z.array(z.string()),
    layouts: z.array(
      z.object({
        name: z.string(),
        label: z.string(),
        fields: z.array(z.record(z.string(), z.unknown())),
        source_method: WordPressAuthoringDiscoveryMethodSchema,
        required_field_names: z.array(z.string()),
        optional_field_names: z.array(z.string())
      })
    ),
    source_method: WordPressAuthoringDiscoveryMethodSchema.nullable().optional(),
    layouts_discovered: z.boolean()
  }),
  dev_content: z.object({
    status: WordPressAuthoringReadinessSchema,
    source_method: WordPressAuthoringDiscoveryMethodSchema.nullable().optional(),
    source_ref: z.string(),
    page_count: z.number(),
    pages: z.array(WordPressAuthoringDevPageSchema).default([]),
    blockers: z.array(WordPressAuthoringBlockerSchema).default([])
  }),
  wp_cli: z.object({
    method: z.literal("wp_cli"),
    status: WordPressAuthoringReadinessSchema,
    configured: z.boolean(),
    missing_env: z.array(z.string()),
    source_refs: z.array(z.string())
  }),
  helper_plugin: z.object({
    method: z.literal("helper"),
    status: WordPressAuthoringReadinessSchema,
    configured: z.boolean(),
    missing_env: z.array(z.string()),
    source_refs: z.array(z.string())
  }),
  write_boundary: z.object({
    allowed_operation: z.literal("create_wordpress_draft"),
    direct_vendor_write_allowed: z.literal(false),
    draft_writes_enabled_by_env: z.boolean(),
    live_write_enabled: z.literal(false),
    publish_allowed: z.literal(false),
    destructive_update_allowed: z.literal(false),
    external_write_attempted: z.literal(false),
    required_action_contract: z.literal("actionobject_validate_preview_review_confirm_audit")
  }),
  discovery_facts: z.array(z.record(z.string(), z.unknown())),
  blockers: z.array(WordPressAuthoringBlockerSchema),
  evidence_ids: z.array(z.string()),
  source_connectors: z.array(z.string())
});

const ContentWordPressAuthoringPayloadPreviewBlockerSchema = z.object({
  code: z.string(),
  label: z.string(),
  reason: z.string(),
  next_step: z.string()
});

type ContentWordPressFieldValuePreviewShape = {
  field_name: string;
  field_label: string;
  field_type: string;
  value_preview?: string | null;
  safe_to_autofill: boolean;
  note?: string | null;
  nested_values: ContentWordPressFieldValuePreviewShape[];
  row_candidates: ContentWordPressFieldRowCandidateShape[];
};

type ContentWordPressRowCandidateFieldShape = {
  field_name: string;
  field_label: string;
  field_type: string;
  value_preview?: string | null;
  safe_to_autofill: boolean;
  note?: string | null;
};

type ContentWordPressFieldRowCandidateShape = {
  row_type: "acf_repeater_row" | "acf_flexible_content_row";
  row_label: string;
  review_status: "review_required";
  note: string;
  field_values: ContentWordPressRowCandidateFieldShape[];
  evidence_ids: string[];
};

const ContentWordPressRowCandidateFieldSchema = z.object({
  field_name: z.string(),
  field_label: z.string(),
  field_type: z.string(),
  value_preview: z.string().nullable().optional(),
  safe_to_autofill: z.boolean(),
  note: z.string().nullable().optional()
});

const ContentWordPressFieldRowCandidateSchema = z.object({
  row_type: z.enum(["acf_repeater_row", "acf_flexible_content_row"]),
  row_label: z.string(),
  review_status: z.literal("review_required"),
  note: z.string(),
  field_values: z.array(ContentWordPressRowCandidateFieldSchema).default([]),
  evidence_ids: z.array(z.string()).default([])
});

const ContentWordPressFieldValuePreviewSchema: z.ZodType<
  ContentWordPressFieldValuePreviewShape
> = z.lazy(() =>
  z.object({
    field_name: z.string(),
    field_label: z.string(),
    field_type: z.string(),
    value_preview: z.string().nullable().optional(),
    safe_to_autofill: z.boolean(),
    note: z.string().nullable().optional(),
    nested_values: z.array(ContentWordPressFieldValuePreviewSchema).default([]),
    row_candidates: z.array(ContentWordPressFieldRowCandidateSchema).default([])
  })
);

const ContentWordPressFlexibleSectionPayloadSchema = z.object({
  layout_name: z.string(),
  layout_label: z.string(),
  section_heading: z.string(),
  field_values: z.record(z.string(), z.string().nullable()),
  field_previews: z.array(ContentWordPressFieldValuePreviewSchema).default([]),
  missing_required_fields: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()).default([])
});

export const ContentWordPressAuthoringPayloadPreviewResultSchema = z.object({
  status: z.enum(["ready", "blocked"]),
  mode: z.literal("dry_run"),
  connector: z.literal("wordpress_ekologus"),
  endpoint_kind: z.literal("posts"),
  post_status: z.literal("draft"),
  flexible_content_field_name: z.string().nullable().optional(),
  sections: z.array(ContentWordPressFlexibleSectionPayloadSchema).default([]),
  publish_allowed: z.literal(false),
  destructive_update_allowed: z.literal(false),
  external_write_attempted: z.literal(false),
  required_action_contract: z.literal("actionobject_validate_preview_review_confirm_audit"),
  blockers: z.array(ContentWordPressAuthoringPayloadPreviewBlockerSchema).default([])
});

export const ContentWorkItemWordPressAuthoringPayloadPreviewRequestSchema = z.object({
  handoff: ContentWordPressDraftHandoffSchema.nullable().optional(),
  draft_package: ContentDraftPackageSchema.nullable().optional(),
  authoring_profile: WordPressAuthoringProfileSchema.nullable().optional()
});

export const ContentWorkItemWordPressAuthoringPayloadPreviewResponseSchema = z.object({
  authoring_profile: WordPressAuthoringProfileSchema,
  preview_result: ContentWordPressAuthoringPayloadPreviewResultSchema
});

export const SocialDraftContextSchema = z.object({
  mode: z.literal("review_only"),
  publish_allowed: z.literal(false),
  missing_publish_access: z.record(z.string(), z.array(z.string())),
  draft_action_ids: z.array(z.string()),
  source_inputs: z.array(z.record(z.string(), z.unknown())),
  draft_constraints: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  source_metric_names: z.array(z.string()).optional(),
  source_connectors: z.array(z.string()).optional(),
  evidence_ids: z.array(z.string()).optional(),
  historical_social_inventory_status: z.enum(["missing", "invalid", "review_ready"]),
  historical_social_inventory_status_label: z.string(),
  duplicate_risk_status: z.literal("blocked_until_social_history_review"),
  duplicate_risk_status_label: z.string(),
  required_history_sources: z.array(z.enum(["linkedin", "facebook"])),
  missing_history_evidence: z.array(z.string()),
  social_history_inventory: SocialHistoryInventorySchema,
  history_audit_endpoint: z.literal("/api/social/history-inventory/audit"),
  history_audit_contract: z.literal("social_history_inventory_v1"),
  operator_next_step: z.string()
});

export const SocialPublisherContextPackSchema = z.object({
  strict_instruction: z.string(),
  connector_status: z.array(ConnectorStatusSchema),
  active_action_objects: z.array(ActionObjectSchema),
  evidence_summaries: z.array(EvidenceSchema),
  social_draft_context: SocialDraftContextSchema
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

export type MetricFact = z.infer<typeof MetricFactSchema>;
export type Opportunity = z.infer<typeof OpportunitySchema>;
export type CommandCenterResponse = z.infer<typeof CommandCenterResponseSchema>;
export type CommandCenterBriefItem = z.infer<typeof CommandCenterBriefItemSchema>;
export type CommandCenterDemoStep = z.infer<typeof CommandCenterDemoStepSchema>;
export type CommandCenterActionPlanItem = z.infer<typeof CommandCenterActionPlanItemSchema>;
export type DailyDecision = z.infer<typeof DailyDecisionSchema>;
export type WorkOrder = z.infer<typeof WorkOrderSchema>;
export type DailyCheckConnectorRef = z.infer<typeof DailyCheckConnectorRefSchema>;
export type DailyCheckItem = z.infer<typeof DailyCheckItemSchema>;
export type DailyCheckResult = z.infer<typeof DailyCheckResultSchema>;
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
export type Workflow = z.infer<typeof WorkflowSchema>;
export type WorkflowRun = z.infer<typeof WorkflowRunSchema>;
export type DemandGenReadinessContract = z.infer<typeof DemandGenReadinessContractSchema>;
export type SocialHistoryInventorySource = z.infer<typeof SocialHistoryInventorySourceSchema>;
export type SocialHistoryDiscoverySeed = z.infer<typeof SocialHistoryDiscoverySeedSchema>;
export type SocialHistoryInventory = z.infer<typeof SocialHistoryInventorySchema>;
export type WordPressAuthoringProfile = z.infer<typeof WordPressAuthoringProfileSchema>;
export type ContentWordPressAuthoringPayloadPreviewResult = z.infer<
  typeof ContentWordPressAuthoringPayloadPreviewResultSchema
>;
export type ContentWorkItemWordPressAuthoringPayloadPreviewRequest = z.input<
  typeof ContentWorkItemWordPressAuthoringPayloadPreviewRequestSchema
>;
export type ContentWorkItemWordPressAuthoringPayloadPreviewResponse = z.infer<
  typeof ContentWorkItemWordPressAuthoringPayloadPreviewResponseSchema
>;
export type SocialDraftContext = z.infer<typeof SocialDraftContextSchema>;
export type SocialPublisherContextPack = z.infer<typeof SocialPublisherContextPackSchema>;
export type ContextPackResponse = z.infer<typeof ContextPackResponseSchema>;
export type ExpertRule = z.infer<typeof ExpertRuleSchema>;
export type ExpertRuleSummary = z.infer<typeof ExpertRuleSummarySchema>;
export type ExpertCapability = z.infer<typeof ExpertCapabilitySchema>;
export type KnowledgeTaxonomyType = z.infer<typeof KnowledgeTaxonomyTypeSchema>;
export type KnowledgeTaxonomyEntry = z.infer<typeof KnowledgeTaxonomyEntrySchema>;
export type ExpertKnowledgeSource = z.infer<typeof ExpertKnowledgeSourceSchema>;
export type KnowledgeCard = z.infer<typeof KnowledgeCardSchema>;
export type KnowledgeDecisionBinding = z.infer<typeof KnowledgeDecisionBindingSchema>;
export type KnowledgeOperatingMapResponse = z.infer<typeof KnowledgeOperatingMapResponseSchema>;
export type MarketingPlaybook = z.infer<typeof MarketingPlaybookSchema>;
export type KnowledgeCompilerResult = z.infer<typeof KnowledgeCompilerResultSchema>;
