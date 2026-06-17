import { z } from "zod";

export const ConnectorStatusSchema = z.object({
  id: z.string(),
  label: z.string(),
  status: z.string(),
  configured: z.boolean(),
  missing_credentials: z.array(z.string()),
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
  unit: z.string().nullable().optional()
});

export const OpportunitySchema = z.object({
  id: z.string(),
  type: z.string(),
  title: z.string(),
  domain: z.string(),
  source_connectors: z.array(z.string()).min(1),
  evidence_ids: z.array(z.string()).min(1),
  metrics: z.array(MetricFactSchema),
  human_diagnosis: z.string().min(1),
  recommended_action: z.string(),
  risk: z.string(),
  action_ids: z.array(z.string()),
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
  payload: z.record(z.unknown()),
  audit_events: z.array(AuditEventSchema)
});

export const ConnectorSummarySchema = z.object({
  total: z.number(),
  configured: z.number(),
  missing_credentials: z.number()
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

export const CommandCenterResponseSchema = z.object({
  strict_instruction: z.string(),
  connector_summary: ConnectorSummarySchema,
  sections: z.record(z.array(OpportunitySchema)),
  active_actions: z.array(ActionObjectSchema),
  connector_health: z.array(ConnectorStatusSchema),
  codex_operator_status: z.record(z.unknown())
});

export const WorkflowSchema = z.object({
  id: z.string(),
  label: z.string(),
  description: z.string()
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
  knowledge_card_summaries: z.array(KnowledgeCardSchema),
  expert_rule_summaries: z.array(ExpertRuleSummarySchema),
  expert_capabilities: z.array(ExpertCapabilitySchema),
  strict_instruction: z.string()
});

export type ConnectorStatus = z.infer<typeof ConnectorStatusSchema>;
export type Opportunity = z.infer<typeof OpportunitySchema>;
export type ActionObject = z.infer<typeof ActionObjectSchema>;
export type CommandCenterResponse = z.infer<typeof CommandCenterResponseSchema>;
export type Workflow = z.infer<typeof WorkflowSchema>;
export type WorkflowRun = z.infer<typeof WorkflowRunSchema>;
export type ContextPackResponse = z.infer<typeof ContextPackResponseSchema>;
export type ExpertRule = z.infer<typeof ExpertRuleSchema>;
export type ExpertRuleSummary = z.infer<typeof ExpertRuleSummarySchema>;
export type ExpertCapability = z.infer<typeof ExpertCapabilitySchema>;
export type KnowledgeCard = z.infer<typeof KnowledgeCardSchema>;
export type MarketingPlaybook = z.infer<typeof MarketingPlaybookSchema>;
export type KnowledgeCompilerResult = z.infer<typeof KnowledgeCompilerResultSchema>;
