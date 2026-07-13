import { z } from "zod";

import { ActionObjectSchema } from "./actions";
import { ConnectorStatusSchema, ConnectorSummarySchema, FreshnessStateSchema, MetricFactSchema } from "./connectors";
import { DecisionStateSchema, OpportunitySchema } from "./core_contracts";

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


