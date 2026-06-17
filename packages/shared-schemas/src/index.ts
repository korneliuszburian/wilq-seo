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

export const ContextPackResponseSchema = z.object({
  current_product_rules: z.array(z.string()),
  available_connectors: z.array(z.string()),
  connector_status: z.array(ConnectorStatusSchema),
  top_opportunities: z.array(OpportunitySchema),
  active_action_objects: z.array(ActionObjectSchema),
  knowledge_card_summaries: z.array(z.record(z.unknown())),
  strict_instruction: z.string()
});

export type ConnectorStatus = z.infer<typeof ConnectorStatusSchema>;
export type Opportunity = z.infer<typeof OpportunitySchema>;
export type ActionObject = z.infer<typeof ActionObjectSchema>;
export type CommandCenterResponse = z.infer<typeof CommandCenterResponseSchema>;
export type Workflow = z.infer<typeof WorkflowSchema>;
export type ContextPackResponse = z.infer<typeof ContextPackResponseSchema>;
