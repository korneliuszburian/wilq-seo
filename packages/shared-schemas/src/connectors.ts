import { z } from "zod";

export const ConnectorRefreshStateSchema = z.object({
  state: z.enum(["queued", "running", "ready", "stale", "partial", "failed", "blocked", "unknown"]),
  state_label: z.string(),
  refresh_allowed: z.boolean(),
  last_run_id: z.string().nullable().optional(),
  last_run_status: z.enum(["queued", "running", "completed", "blocked", "failed"]).nullable().optional(),
  last_run_started_at: z.string().nullable().optional(),
  last_run_completed_at: z.string().nullable().optional(),
  safe_next_step: z.string(),
  affected_decisions: z.array(z.string()),
  automatic_refresh: z.object({
    eligible: z.boolean(),
    reason: z.enum([
      "eligible_stale",
      "not_stale",
      "active_run",
      "cooldown",
      "missing_credentials",
      "not_configured",
      "read_unavailable",
      "partial_read",
      "failed_read",
      "blocked_read",
      "unknown_state"
    ]),
    reason_label: z.string(),
    safe_next_step: z.string(),
    cooldown_seconds: z.number()
  })
});

export const ConnectorStatusSchema = z.object({
  id: z.string(),
  label: z.string(),
  status: z.string(),
  status_label: z.string().default(""),
  product_scope: z
    .enum(["production", "optional_disabled", "experimental", "runtime"])
    .default("production"),
  product_scope_label: z.string().default(""),
  active_for_daily_work: z.boolean().default(true),
  configured: z.boolean(),
  missing_credentials: z.array(z.string()),
  missing_credentials_summary_label: z.string().default(""),
  available_credential_sources: z.array(z.string()),
  credential_source_summary_label: z.string().default(""),
  freshness: z.object({ state: z.string(), notes: z.string().nullable().optional() }),
  refresh_state: ConnectorRefreshStateSchema.default({
    state: "unknown",
    state_label: "stan odświeżenia do sprawdzenia",
    refresh_allowed: false,
    safe_next_step: "Sprawdź stan źródła przed użyciem danych w decyzji.",
    affected_decisions: [],
    automatic_refresh: {
      eligible: false,
      reason: "unknown_state",
      reason_label: "Automatyczne odświeżenie wymaga sprawdzenia.",
      safe_next_step: "Sprawdź stan źródła przed automatycznym odczytem.",
      cooldown_seconds: 900
    }
  }),
  error: z.string().nullable().optional(),
  rate_limit_notes: z.string().nullable().optional(),
  cost_notes: z.string().nullable().optional(),
  risk_notes: z.string().nullable().optional(),
  health_check: z.string().default(""),
  capabilities: z.object({
    read: z.boolean(),
    write: z.boolean(),
    read_adapter: z.string().nullable(),
    mutation_adapter: z.string().nullable(),
    action_scope: z.enum(["read_only", "review_only", "draft_only", "disabled"]),
    blockers: z.array(z.string()),
    operations: z.array(z.string())
  }),
  supported_actions: z.array(z.string())
});

export const FreshnessStateSchema = z.object({
  state: z.enum(["fresh", "stale", "unknown", "missing"]),
  last_success_at: z.string().nullable().optional(),
  checked_at: z.string().nullable().optional(),
  notes: z.string().nullable().optional()
});

export const MetricStoreStatusSchema = z.object({
  backend: z.string(),
  enabled: z.boolean(),
  path_configured: z.boolean(),
  metric_fact_count: z.number(),
  connector_count: z.number(),
  refresh_run_count: z.number()
});

export const MetricFactSchema = z.object({
  name: z.string(),
  metric_label: z.string().default(""),
  value: z.union([z.string(), z.number()]),
  period: z.string(),
  source_connector: z.string(),
  evidence_id: z.string(),
  dimensions: z.record(z.string(), z.string()).optional().default({}),
  dimension_labels: z.record(z.string(), z.string()).optional().default({}),
  dimension_value_labels: z.record(z.string(), z.string()).optional().default({}),
  unit: z.string().nullable().optional(),
  collected_at: z.string().nullable().optional(),
  previous_value: z.union([z.string(), z.number()]).nullable().optional(),
  delta: z.number().nullable().optional(),
  delta_percent: z.number().nullable().optional(),
  trend: z.enum(["up", "down", "flat", "unknown"]).optional(),
  freshness_state: z.enum(["fresh", "stale", "unknown"]).optional(),
  freshness_label: z.string().nullable().optional()
});

export const EvidenceSchema = z.object({
  id: z.string(),
  title_label: z.string().default(""),
  source_connector: z.string(),
  source_connector_label: z.string().default(""),
  source_type: z.string(),
  source_type_label: z.string().default(""),
  source_id: z.string(),
  collected_at: z.string(),
  freshness: z.object({ state: z.string(), notes: z.string().nullable().optional() }),
  freshness_label: z.string().default(""),
  summary: z.string(),
  trace_summary_label: z.string().default(""),
  raw_ref: z.string().nullable().optional()
});

export const ConnectorRefreshRunSchema = z.object({
  id: z.string(),
  connector_id: z.string(),
  connector_label: z.string().default(""),
  mode: z.enum(["status_probe", "vendor_read"]),
  status: z.enum(["queued", "running", "completed", "blocked", "failed"]),
  status_label: z.string().default(""),
  started_at: z.string(),
  completed_at: z.string().nullable().optional(),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  missing_credentials: z.array(z.string()),
  checked_credentials: z.array(z.string()),
  external_call_attempted: z.boolean(),
  vendor_data_collected: z.boolean(),
  metrics_persisted: z.boolean().default(true),
  metric_summary: z.record(z.string(), z.union([z.string(), z.number()])),
  covered_window: z
    .object({
      date_start: z.string().nullable().optional(),
      date_end: z.string().nullable().optional(),
      completeness: z.string().nullable().optional(),
      cap_or_truncation: z.string().nullable().optional(),
      snapshot_date: z.string().nullable().optional(),
      cadence: z.string().nullable().optional(),
      coverage_scope: z.string().nullable().optional(),
      coverage_count: z.number().nullable().optional(),
      requested_count: z.number().nullable().optional(),
      covered_count: z.number().nullable().optional(),
      proxy_source: z.string().nullable().optional(),
      interpretation_caveats: z.array(z.string()).default([])
    })
    .optional(),
  settlement_state: z.enum(["not_applicable", "settling", "settled", "unknown"]).optional(),
  quality_state: z.enum(["verified", "partial", "unverified", "unknown"]).optional(),
  summary: z.string(),
  errors: z.array(z.string()),
  redacted: z.boolean()
});

export const ConnectorSummarySchema = z.object({
  total: z.number(),
  configured: z.number(),
  missing_credentials: z.number()
});

export type ConnectorStatus = z.infer<typeof ConnectorStatusSchema>;
export type MetricFact = z.infer<typeof MetricFactSchema>;
export type MetricStoreStatus = z.infer<typeof MetricStoreStatusSchema>;
export type Evidence = z.infer<typeof EvidenceSchema>;
export type ConnectorRefreshRun = z.infer<typeof ConnectorRefreshRunSchema>;
