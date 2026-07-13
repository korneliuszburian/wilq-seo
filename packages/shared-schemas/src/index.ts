import { z } from "zod";

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
  EvidenceSchema
  ,MetricFactSchema
} from "./connectors";
import {
  ActionObjectSchema
} from "./actions";
import {
  MarketingBriefSchema,
  TacticalQueueResponseSchema
} from "./marketing";
import {
  AdsAccountCurrencyReadContractSchema,
  AdsBudgetPacingReadContractSchema,
  AdsBudgetPacingRowSchema,
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
import { OpportunitySchema } from "./core_contracts";
import {
  CommandCenterActionPlanItemSchema,
  CommandCenterBriefItemSchema,
  CommandCenterDemoStepSchema,
  CommandCenterResponseSchema,
  DailyCheckConnectorRefSchema,
  DailyCheckItemSchema,
  DailyCheckResultSchema,
  DailyDecisionSchema,
  WorkOrderSchema
} from "./command_center";
import {
  WorkflowRunSchema,
  WorkflowSchema
} from "./workflow_contracts";
import { DemandGenReadinessContractSchema } from "./demand_gen";
import {
  SocialHistoryDiscoverySeedSchema,
  SocialHistoryInventorySchema,
  SocialHistoryInventorySourceSchema
} from "./social_history";
import {
  ContentWordPressAuthoringPayloadPreviewResultSchema,
  ContentWorkItemWordPressAuthoringPayloadPreviewRequestSchema,
  ContentWorkItemWordPressAuthoringPayloadPreviewResponseSchema,
  WordPressAuthoringProfileSchema
} from "./wordpress_authoring";
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
export * from "./core_contracts";
export * from "./command_center";
export * from "./workflow_contracts";
export * from "./demand_gen";
export * from "./social_history";
export * from "./wordpress_authoring";
export * from "./merchant_diagnostics";







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
