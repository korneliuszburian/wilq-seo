import { z } from "zod";

import { MetricFactSchema } from "./connectors";

export const DiagnosticDataReadinessSchema = z.object({
  state: z.enum([
    "ready",
    "partial",
    "refresh_available",
    "refresh_running",
    "unavailable",
    "missing",
    "blocked",
    "failed"
  ]),
  state_label: z.string(),
  reason: z.string(),
  coverage_label: z.string(),
  refresh_allowed: z.boolean(),
  safe_next_step: z.string(),
  factual_metric_count: z.number().int().nonnegative(),
  factual_metrics: z.array(MetricFactSchema),
  evidence_ids: z.array(z.string()),
  connector_id: z.string(),
  connector_label: z.string(),
  latest_refresh_id: z.string().nullable()
});

export type DiagnosticDataReadiness = z.infer<typeof DiagnosticDataReadinessSchema>;
