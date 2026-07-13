import { z } from "zod";

import { ConnectorRefreshRunSchema, ConnectorStatusSchema, MetricFactSchema } from "./connectors";

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


