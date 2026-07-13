import { z } from "zod";

import { MetricFactSchema } from "./connectors";

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
















