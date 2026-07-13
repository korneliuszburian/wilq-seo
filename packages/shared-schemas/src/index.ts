import { z } from "zod";

import {
  ContentDraftPackageSchema,
  ContentWordPressDraftHandoffSchema
} from "./contentWorkflow";
import {
  ContentAhrefsCandidateRowSchema,
  ContentDiagnosticSectionSchema,
  ContentDiagnosticsResponseSchema,
} from "./content_diagnostics";
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
  TacticalQueueItemSchema,
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
  MerchantDecisionItemSchema,
  MerchantDiagnosticSectionSchema,
  MerchantDiagnosticsResponseSchema
} from "./merchant_diagnostics";

export * from "./contentWorkflow";
export * from "./content_diagnostics";
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
  evidence_summary_label: z.string().default(""),
  source_connectors: z.array(z.string()),
  source_connector_labels: z.array(z.string()).default([]),
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
  source_connector_labels: z.array(z.string()).default([]),
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
  metric_tiles: z.record(z.string(), z.union([z.string(), z.number()])),
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
  action_summary_label: z.string().default(""),
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
  missing_read_contract_summary_label: z.string().optional().default(""),
  conversion_like_metric_count: z.number(),
  dimensioned_behavior_metric_count: z.number(),
  landing_group_count: z.number(),
  source_connectors: z.array(z.string()),
  source_connector_labels: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  action_ids: z.array(z.string()),
  action_summary_label: z.string().default(""),
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
  action_summary_label: z.string().default(""),
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
  evidence_summary_label: z.string().default(""),
  source_connector_labels: z.array(z.string()).default([]),
  action_ids: z.array(z.string()),
  action_summary_label: z.string().default(""),
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
  metric_fact_labels: z.record(z.string(), z.string()).default({}),
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
  metric_tiles: z.record(z.string(), z.union([z.string(), z.number()])).default({}),
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
  metric_fact_labels: z.record(z.string(), z.string()).default({}),
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
  missing_read_contract_summary_label: z.string().default(""),
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
  evidence_summary_label: z.string().default(""),
  metric_facts: z.array(MetricFactSchema),
  metric_fact_labels: z.record(z.string(), z.string()).default({}),
  action_ids: z.array(z.string()),
  action_summary_label: z.string().default(""),
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
  metric_tiles: z.record(z.string(), z.union([z.string(), z.number()])).default({}),
  allowed_evidence: z.array(z.string()),
  allowed_evidence_labels: z.array(z.string()).default([]),
  missing_read_contracts: z.array(z.string()),
  missing_read_contract_labels: z.array(z.string()).default([]),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  metric_facts: z.array(MetricFactSchema),
  metric_fact_labels: z.record(z.string(), z.string()).default({}),
  action_ids: z.array(z.string()),
  action_summary_label: z.string().default(""),
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
  metric_fact_labels: z.record(z.string(), z.string()).default({}),
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
  missing_read_contract_summary_label: z.string().default(""),
  allowed_evidence: z.array(z.string()),
  allowed_evidence_labels: z.array(z.string()).default([]),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).default([]),
  blocked_claim_summary_label: z.string().default(""),
  operator_review_gates: z.array(z.string()),
  operator_review_gate_labels: z.array(z.string()).default([]),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  action_ids: z.array(z.string()).default([]),
  action_summary_label: z.string().default(""),
  gap_records: z.array(AhrefsGapRecordSchema),
  gap_record_count: z.number(),
  cross_check_status: z.enum(["api_backed", "manual_required", "missing"]).default("missing"),
  cross_check_status_label: z.string().default(""),
  cross_check_summary: z.string().default(""),
  cross_check_next_step: z.string().default(""),
  cross_check_gsc_match_count: z.number().default(0),
  cross_check_wordpress_match_count: z.number().default(0),
  cross_check_source_connectors: z.array(z.string()).default([]),
  cross_check_evidence_ids: z.array(z.string()).default([]),
  cross_check_candidates: z.array(ContentAhrefsCandidateRowSchema).default([]),
  next_step: z.string(),
  risk: z.enum(["low", "medium", "high", "critical"])
});

export const AhrefsOperatorSummarySchema = z.object({
  id: z.literal("ahrefs_operator_summary"),
  title: z.string(),
  summary: z.string(),
  next_step: z.string(),
  review_card_label: z.string().default("Karta review Ahrefs"),
  review_decision_after_review: z.string().default(""),
  review_question_for_operator: z.string().default(""),
  review_next_safe_click: z.string().default(""),
  review_action_ids: z.array(z.string()).default([]),
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
  evidence_summary_label: z.string().default(""),
  action_ids: z.array(z.string()),
  action_summary_label: z.string().default(""),
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
  action_summary_label: z.string().default(""),
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
  source_ids: z.array(z.string()).default([]),
  requires_evidence: z.boolean()
});

export const ExpertRuleSummarySchema = z.object({
  id: z.string(),
  name: z.string(),
  domain: z.string(),
  source_anchor: z.string(),
  required_inputs: z.array(z.string()),
  recommended_actions: z.array(z.string()),
  source_ids: z.array(z.string()).default([]),
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

export const KnowledgeTaxonomyTypeSchema = z.enum([
  "client_truth",
  "expert_operating",
  "platform_trap",
  "workspace_memory",
  "observed_outcome"
]);

export const KnowledgeTaxonomyEntrySchema = z.object({
  id: KnowledgeTaxonomyTypeSchema,
  label: z.string().default(""),
  definition: z.string(),
  owned_by: z.enum([
    "source_fact_compiler",
    "expert_rule_compiler",
    "platform_rule_pack",
    "workspace_dossier",
    "measurement_loop"
  ]),
  allowed_usage: z.array(z.string()).default([]),
  forbidden_usage: z.array(z.string()).default([]),
  example_records: z.array(z.string()).default([])
}).superRefine((entry, ctx) => {
  const expectedOwnerByType: Record<z.infer<typeof KnowledgeTaxonomyTypeSchema>, string> = {
    client_truth: "source_fact_compiler",
    expert_operating: "expert_rule_compiler",
    platform_trap: "platform_rule_pack",
    workspace_memory: "workspace_dossier",
    observed_outcome: "measurement_loop"
  };
  if (entry.owned_by !== expectedOwnerByType[entry.id]) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["owned_by"],
      message: `Knowledge taxonomy type ${entry.id} must be owned by ${expectedOwnerByType[entry.id]}`
    });
  }
});

export const ExpertKnowledgeSourceSchema = z.object({
  id: z.string(),
  domain: z.string(),
  knowledge_type: KnowledgeTaxonomyTypeSchema,
  source_type: z.enum([
    "official_platform_doc",
    "repo_structured_rule",
    "reviewed_internal_sop",
    "public_site",
    "measurement_evidence",
    "workspace_memory"
  ]),
  license_status: z.enum([
    "commit_safe",
    "review_required",
    "private_reference_only"
  ]),
  source_reference: z.string(),
  freshness_date: z.string(),
  reviewer: z.string().nullable().optional(),
  trust_level: z.enum(["low", "medium", "high"]).default("medium"),
  allowed_usage: z.array(z.string()).min(1),
  forbidden_usage: z.array(z.string()).min(1),
  linked_rule_ids: z.array(z.string()).min(1)
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
  metric_tiles: z.record(z.string(), z.union([z.string(), z.number()])),
  knowledge_card_ids: z.array(z.string()),
  playbook_ids: z.array(z.string()),
  expert_rule_ids: z.array(z.string()),
  knowledge_summary_label: z.string().default(""),
  required_evidence: z.array(z.string()),
  required_evidence_summary_label: z.string().default(""),
  missing_contracts: z.array(z.string()),
  missing_contract_labels: z.array(z.string()).default([]),
  missing_contract_summary_label: z.string().default(""),
  missing_contract_detail_label: z.string().default(""),
  has_missing_contracts: z.boolean().default(false),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).default([]),
  blocked_claim_summary_label: z.string().default(""),
  blocked_claim_count_summary_label: z.string().default(""),
  has_blocked_claims: z.boolean().default(false),
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
  blocked_binding_summary_label: z.string().default(""),
  missing_contract_summary_label: z.string().default(""),
  blocked_claim_count_summary_label: z.string().default(""),
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
