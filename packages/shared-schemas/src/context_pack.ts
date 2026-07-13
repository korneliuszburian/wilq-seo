import { z } from "zod";

import { ActionObjectSchema } from "./actions";
import { ConnectorRefreshRunSchema, ConnectorStatusSchema, EvidenceSchema } from "./connectors";
import { OpportunitySchema } from "./core_contracts";
import { CommandCenterResponseSchema } from "./command_center";
import { MarketingBriefSchema, TacticalQueueResponseSchema } from "./marketing";
import { AdsDiagnosticsResponseSchema } from "./ads_diagnostics";
import { MerchantDiagnosticsResponseSchema } from "./merchant_diagnostics";
import { ContentDiagnosticsResponseSchema } from "./content_diagnostics";
import { ContentPreflightResponseSchema } from "./content_preflight";
import { Ga4DiagnosticsResponseSchema } from "./ga4_diagnostics";
import { LocaloDiagnosticsResponseSchema } from "./localo_diagnostics";
import { AhrefsDiagnosticsResponseSchema } from "./ahrefs_diagnostics";
import { DemandGenReadinessContractSchema } from "./demand_gen";
import { KnowledgeCardSchema } from "./knowledge_contracts";
import { ExpertRuleSummarySchema, ExpertCapabilitySchema } from "./expert_contracts";

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

