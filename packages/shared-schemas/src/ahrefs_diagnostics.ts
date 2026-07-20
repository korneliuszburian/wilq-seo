import { z } from "zod";

import { ConnectorRefreshRunSchema, ConnectorStatusSchema, MetricFactSchema } from "./connectors";
import { ContentAhrefsCandidateRowSchema } from "./content_diagnostics";

export const AhrefsRequestBudgetSchema = z.object({
  estimated_calls: z.number().int().nonnegative(),
  failed_stages: z.number().int().nonnegative(),
  partial: z.boolean(),
  summary: z.string(),
  stages: z.array(
    z.object({
      id: z.enum([
        "domain_rating",
        "organic_competitors",
        "top_pages_by_competitor",
        "organic_keywords_by_url",
        "content_gap",
        "backlink_gap"
      ]),
      label: z.string(),
      status: z.enum(["completed", "failed", "skipped", "not_run"]),
      status_label: z.string().default(""),
      requested_calls: z.number().int().nonnegative(),
      rows: z.number().int().nonnegative(),
      summary: z.string()
    })
  ).default([])
});

export const AhrefsDiagnosticSectionSchema = z.object({
  id: z.string(),
  title: z.string(),
  status: z.enum(["ready", "blocked", "missing"]),
  status_label: z.string().default(""),
  summary: z.string(),
  diagnosis: z.string(),
  next_step: z.string(),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  metric_facts: z.array(MetricFactSchema),
  metric_fact_labels: z.record(z.string(), z.string()).default({}),
  action_ids: z.array(z.string()),
  action_summary_label: z.string().default(""),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).default([]),
  risk: z.enum(["low", "medium", "high", "critical"])
});

export const AhrefsDecisionItemSchema = z.object({
  id: z.string(),
  decision_type: z.enum([
    "review_authority_context",
    "review_gap_records",
    "run_authority_read",
    "block_gap_claims"
  ]),
  status: z.enum(["ready", "blocked"]),
  status_label: z.string().default(""),
  decision_type_label: z.string().default(""),
  title: z.string(),
  summary: z.string(),
  rationale: z.string(),
  next_step: z.string(),
  priority: z.number(),
  priority_label: z.string().default(""),
  metric_tiles: z.record(z.string(), z.union([z.string(), z.number()])).default({}),
  allowed_evidence: z.array(z.string()),
  allowed_evidence_labels: z.array(z.string()).default([]),
  missing_read_contracts: z.array(z.string()),
  missing_read_contract_labels: z.array(z.string()).default([]),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  metric_facts: z.array(MetricFactSchema),
  metric_fact_labels: z.record(z.string(), z.string()).default({}),
  action_ids: z.array(z.string()),
  action_summary_label: z.string().default(""),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).default([]),
  risk: z.enum(["low", "medium", "high", "critical"])
});

export const AhrefsGapRecordSchema = z.object({
  id: z.string(),
  gap_type: z.enum([
    "competitor_page",
    "content_gap",
    "backlink_gap",
    "organic_keyword_gap",
    "top_page_gap"
  ]),
  gap_type_label: z.string().default(""),
  title: z.string(),
  summary: z.string(),
  source_url: z.string().nullable().optional(),
  referenced_public_url: z.string().nullable().optional(),
  competitor_domain: z.string().nullable().optional(),
  keyword: z.string().nullable().optional(),
  mapping_status: z.enum(["unbound", "review_required", "exact"]).optional(),
  derived_method: z.string().optional(),
  coverage_summary: z.string().optional(),
  metric_facts: z.array(MetricFactSchema),
  metric_fact_labels: z.record(z.string(), z.string()).default({}),
  evidence_ids: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  next_step: z.string(),
  risk: z.enum(["low", "medium", "high", "critical"])
});

export const AhrefsGapReadContractSchema = z.object({
  id: z.literal("ahrefs_gap_read_contract"),
  status: z.enum(["ready", "blocked"]),
  status_label: z.string().default(""),
  title: z.string(),
  summary: z.string(),
  available_read_contracts: z.array(z.string()),
  available_read_contract_labels: z.array(z.string()).default([]),
  missing_read_contracts: z.array(z.string()),
  missing_read_contract_labels: z.array(z.string()).default([]),
  missing_read_contract_summary_label: z.string().default(""),
  allowed_evidence: z.array(z.string()),
  allowed_evidence_labels: z.array(z.string()).default([]),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).default([]),
  blocked_claim_summary_label: z.string().default(""),
  operator_review_gates: z.array(z.string()),
  operator_review_gate_labels: z.array(z.string()).default([]),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  action_ids: z.array(z.string()).default([]),
  action_summary_label: z.string().default(""),
  gap_records: z.array(AhrefsGapRecordSchema),
  gap_record_count: z.number(),
  coverage_summary: z.string().default(""),
  cross_check_status: z.enum(["api_backed", "manual_required", "missing"]).default("missing"),
  cross_check_status_label: z.string().default(""),
  cross_check_summary: z.string().default(""),
  cross_check_next_step: z.string().default(""),
  cross_check_gsc_match_count: z.number().default(0),
  cross_check_wordpress_match_count: z.number().default(0),
  cross_check_source_connectors: z.array(z.string()).default([]),
  cross_check_evidence_ids: z.array(z.string()).default([]),
  cross_check_candidates: z.array(ContentAhrefsCandidateRowSchema).default([]),
  next_step: z.string(),
  risk: z.enum(["low", "medium", "high", "critical"])
});

export const AhrefsOperatorSummarySchema = z.object({
  id: z.literal("ahrefs_operator_summary"),
  title: z.string(),
  summary: z.string(),
  next_step: z.string(),
  review_card_label: z.string().default("Karta review Ahrefs"),
  review_decision_after_review: z.string().default(""),
  review_question_for_operator: z.string().default(""),
  review_next_safe_click: z.string().default(""),
  review_action_ids: z.array(z.string()).default([]),
  top_decision_ids: z.array(z.string()),
  gap_read_status: z.enum(["ready", "blocked"]),
  gap_read_status_label: z.string().default(""),
  authority_fact_count: z.number(),
  gap_fact_count: z.number(),
  available_read_contracts: z.array(z.string()),
  available_read_contract_labels: z.array(z.string()).default([]),
  missing_read_contracts: z.array(z.string()),
  missing_read_contract_labels: z.array(z.string()).default([]),
  source_connectors: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  action_ids: z.array(z.string()),
  action_summary_label: z.string().default(""),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).default([])
});

export const AhrefsDiagnosticsResponseSchema = z.object({
  generated_at: z.string().nullable().optional(),
  language: z.literal("pl-PL"),
  strict_instruction: z.string(),
  connector: ConnectorStatusSchema,
  connector_status_label: z.string().default(""),
  latest_refresh: ConnectorRefreshRunSchema.nullable().optional(),
  latest_refresh_status_label: z.string().nullable().optional(),
  request_budget: AhrefsRequestBudgetSchema.optional(),
  live_data_status_label: z.string().default(""),
  live_data_available: z.boolean(),
  authority_fact_count: z.number(),
  gap_fact_count: z.number(),
  gap_read_contract: AhrefsGapReadContractSchema,
  operator_summary: AhrefsOperatorSummarySchema,
  decision_queue: z.array(AhrefsDecisionItemSchema),
  sections: z.array(AhrefsDiagnosticSectionSchema),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  source_connector_labels: z.array(z.string()).default([]),
  action_ids: z.array(z.string()),
  action_summary_label: z.string().default(""),
  blocker_count: z.number()
});
