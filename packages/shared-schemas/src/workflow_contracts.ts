import { z } from "zod";

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

