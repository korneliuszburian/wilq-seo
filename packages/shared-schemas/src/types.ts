import { z } from "zod";

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
  WorkOrderSchema,
} from "./command_center";
import {
  AdsAccountCurrencyReadContractSchema,
  AdsBudgetPacingReadContractSchema,
  AdsBudgetPacingRowSchema,
  AdsDiagnosticSectionSchema,
  AdsSharedBudgetDistributionRowSchema,
} from "./ads_campaigns";
import {
  AdsKeywordMatchContextReadContractSchema,
  AdsKeywordMatchContextRowSchema,
} from "./ads_keyword_contracts";
import {
  AdsCustomSegmentCandidateSchema,
  AdsCustomSegmentsReadContractSchema,
} from "./ads_custom_segments";
import {
  AdsNegativeKeywordCandidateSchema,
  AdsNegativeKeywordPayloadPreviewSchema,
  AdsNegativeKeywordsReadContractSchema,
} from "./ads_negative_keywords";
import { AdsDiagnosticsResponseSchema } from "./ads_diagnostics";
import {
  MerchantDecisionItemSchema,
  MerchantDiagnosticSectionSchema,
  MerchantDiagnosticsResponseSchema,
} from "./merchant_diagnostics";
import {
  ContentDiagnosticSectionSchema,
  ContentDiagnosticsResponseSchema,
} from "./content_diagnostics";
import { ContentPreflightResponseSchema } from "./content_preflight";
import {
  Ga4DecisionItemSchema,
  Ga4DiagnosticSectionSchema,
  Ga4DiagnosticsResponseSchema,
} from "./ga4_diagnostics";
import {
  LocaloAccessProbeSchema,
  LocaloDecisionItemSchema,
  LocaloDiagnosticSectionSchema,
  LocaloDiagnosticsResponseSchema,
} from "./localo_diagnostics";
import {
  AhrefsDecisionItemSchema,
  AhrefsDiagnosticSectionSchema,
  AhrefsDiagnosticsResponseSchema,
} from "./ahrefs_diagnostics";
import { WorkflowRunSchema, WorkflowSchema } from "./workflow_contracts";
import { DemandGenReadinessContractSchema } from "./demand_gen";
import {
  SocialHistoryDiscoverySeedSchema,
  SocialHistoryInventorySchema,
  SocialHistoryInventorySourceSchema,
} from "./social_history";
import {
  ContentWordPressAuthoringPayloadPreviewResultSchema,
  ContentWorkItemWordPressAuthoringPayloadPreviewRequestSchema,
  ContentWorkItemWordPressAuthoringPayloadPreviewResponseSchema,
  WordPressAuthoringProfileSchema,
} from "./wordpress_authoring";
import {
  SocialDraftContextSchema,
  SocialPublisherContextPackSchema,
} from "./social_publisher";
import { ContextPackResponseSchema } from "./context_pack";
import {
  ExpertCapabilitySchema,
  ExpertRuleSchema,
  ExpertRuleSummarySchema,
} from "./expert_contracts";
import {
  ExpertKnowledgeSourceSchema,
  KnowledgeCardSchema,
  KnowledgeCompilerResultSchema,
  KnowledgeDecisionBindingSchema,
  KnowledgeOperatingMapResponseSchema,
  KnowledgeTaxonomyEntrySchema,
  KnowledgeTaxonomyTypeSchema,
  MarketingPlaybookSchema,
} from "./knowledge_contracts";

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
export type AdsAccountCurrencyReadContract = z.infer<typeof AdsAccountCurrencyReadContractSchema>;
export type AdsBudgetPacingRow = z.infer<typeof AdsBudgetPacingRowSchema>;
export type AdsSharedBudgetDistributionRow = z.infer<typeof AdsSharedBudgetDistributionRowSchema>;
export type AdsBudgetPacingReadContract = z.infer<typeof AdsBudgetPacingReadContractSchema>;
export type AdsCustomSegmentCandidate = z.infer<typeof AdsCustomSegmentCandidateSchema>;
export type AdsCustomSegmentsReadContract = z.infer<typeof AdsCustomSegmentsReadContractSchema>;
export type AdsKeywordMatchContextRow = z.infer<typeof AdsKeywordMatchContextRowSchema>;
export type AdsKeywordMatchContextReadContract = z.infer<typeof AdsKeywordMatchContextReadContractSchema>;
export type AdsNegativeKeywordPayloadPreview = z.infer<typeof AdsNegativeKeywordPayloadPreviewSchema>;
export type AdsNegativeKeywordCandidate = z.infer<typeof AdsNegativeKeywordCandidateSchema>;
export type AdsNegativeKeywordsReadContract = z.infer<typeof AdsNegativeKeywordsReadContractSchema>;
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
export type ContentWordPressAuthoringPayloadPreviewResult = z.infer<typeof ContentWordPressAuthoringPayloadPreviewResultSchema>;
export type ContentWorkItemWordPressAuthoringPayloadPreviewRequest = z.input<typeof ContentWorkItemWordPressAuthoringPayloadPreviewRequestSchema>;
export type ContentWorkItemWordPressAuthoringPayloadPreviewResponse = z.infer<typeof ContentWorkItemWordPressAuthoringPayloadPreviewResponseSchema>;
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
