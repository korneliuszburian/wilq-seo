import { z } from "zod";

import { MetricFactSchema } from "./connectors";

export const ContentDraftRevisionBindingSchema = z
  .object({
    work_item_id: z.string().min(1),
    handoff_id: z.string().min(1),
    revision_id: z.string().min(1),
    content_digest: z.string().regex(/^[0-9a-f]{64}$/),
    draft_package_id: z.string().min(1),
    draft_package_digest: z.string().regex(/^[0-9a-f]{64}$/),
    approval_decision_id: z.string().min(1),
    final_canonical_url: z.string().min(1)
  })
  .strict();

export const ActionWordPressDraftApplyBlockerSchema = z.object({
  code: z.string().min(1),
  label: z.string().min(1),
  reason: z.string().min(1),
  next_step: z.string().min(1)
});

export const AuditEventSchema = z.object({
  id: z.string(),
  action_id: z.string().nullable().optional(),
  event_type: z.string(),
  event_type_label: z.string().default(""),
  actor: z.string(),
  created_at: z.string(),
  summary: z.string(),
  evidence_ids: z.array(z.string()),
  details: z.record(z.string(), z.unknown()).default({}),
  redacted: z.boolean()
});

export const ActionReviewOutcomeSchema = z.enum([
  "approved_for_prepare",
  "needs_changes",
  "rejected",
  "deferred"
]);

export const ActionReviewRequestSchema = z.object({
  outcome: ActionReviewOutcomeSchema,
  reviewed_by: z.string().min(1),
  notes: z.string().min(1).max(2000),
  checked_items: z.array(z.string()).default([]),
  blockers: z.array(z.string()).default([]),
  wordpress_draft: ContentDraftRevisionBindingSchema.nullable().optional()
});

export const ActionReviewGateSchema = z.object({
  status: z
    .enum(["pending_validation", "validated_prepare_only", "ready_to_apply", "blocked_apply"])
    .default("pending_validation"),
  status_label: z.string().default(""),
  summary: z.string().default("Wymaga sprawdzenia w WILQ przed kolejnym krokiem."),
  required_checks: z.array(z.string()).default([]),
  required_check_labels: z.array(z.string()).default([]),
  operator_checklist: z.array(z.string()).default([]),
  operator_checklist_labels: z.array(z.string()).default([]),
  apply_blockers: z.array(z.string()).default([]),
  apply_blocker_labels: z.array(z.string()).default([]),
  apply_blocker_summary_label: z.string().optional().default(""),
  confirmation_required: z.boolean().default(true),
  apply_allowed: z.boolean().default(false),
  last_review_outcome: ActionReviewOutcomeSchema.nullable().optional(),
  last_review_outcome_label: z.string().nullable().optional(),
  last_reviewed_by: z.string().nullable().optional(),
  last_reviewed_at: z.string().nullable().optional(),
  last_review_summary: z.string().nullable().optional(),
  last_confirmation_by: z.string().nullable().optional(),
  last_confirmation_at: z.string().nullable().optional(),
  last_confirmation_summary: z.string().nullable().optional(),
  last_impact_check_status: z.enum(["checked", "blocked"]).nullable().optional(),
  last_impact_check_status_label: z.string().nullable().optional(),
  last_impact_checked_by: z.string().nullable().optional(),
  last_impact_checked_at: z.string().nullable().optional(),
  last_impact_check_summary: z.string().nullable().optional(),
  last_mutation_audit_id: z.string().nullable().optional(),
  last_mutation_audit_status: z.enum(["blocked", "applied", "failed"]).nullable().optional(),
  last_mutation_audit_status_label: z.string().nullable().optional(),
  last_mutation_audit_actor: z.string().nullable().optional(),
  last_mutation_audit_at: z.string().nullable().optional(),
  last_mutation_audit_summary: z.string().nullable().optional(),
  last_mutation_adapter_reached: z.boolean().nullable().optional(),
  last_mutation_adapter_reached_label: z.string().nullable().optional(),
  last_external_write_attempted: z.boolean().nullable().optional(),
  last_external_write_attempted_label: z.string().nullable().optional(),
  last_mutation_attempted: z.boolean().nullable().optional(),
  last_mutation_attempted_label: z.string().nullable().optional(),
  last_mutation_adapter: z.string().nullable().optional(),
  last_mutation_adapter_label: z.string().nullable().optional(),
  last_mutation_audit_event_id: z.string().nullable().optional(),
  last_mutation_audit_trace_label: z.string().nullable().optional(),
  last_mutation_blockers: z.array(z.string()).default([]),
  last_mutation_blocker_labels: z.array(z.string()).default([]),
  last_mutation_blocker_summary_label: z.string().optional().default("")
});

const DEFAULT_ACTION_REVIEW_GATE = {
  status: "pending_validation",
  status_label: "",
  summary: "Wymaga sprawdzenia w WILQ przed kolejnym krokiem.",
  required_checks: [],
  required_check_labels: [],
  operator_checklist: [],
  operator_checklist_labels: [],
  apply_blockers: [],
  apply_blocker_labels: [],
  apply_blocker_summary_label: "",
  confirmation_required: true,
  apply_allowed: false,
  last_mutation_blockers: [],
  last_mutation_blocker_labels: [],
  last_mutation_blocker_summary_label: ""
} satisfies z.input<typeof ActionReviewGateSchema>;

export const ActionPreviewRowViewModelSchema = z.object({
  label: z.string(),
  value: z.string()
});

export const ActionPreviewCardViewModelSchema = z.object({
  id: z.string(),
  kind: z.string(),
  title_label: z.string(),
  subtitle_label: z.string().default(""),
  status_label: z.string().default(""),
  rows: z.array(ActionPreviewRowViewModelSchema).default([]),
  apply_state_label: z.string().default(""),
  system_readiness_label: z.string().default("")
});

export const ActionPreviewItemViewModelSchema = z.object({
  id: z.string(),
  title_label: z.string(),
  status_label: z.string().default(""),
  rows: z.array(ActionPreviewRowViewModelSchema).default([])
});

export const ActionDomainSchema = z.enum([
  "google_ads",
  "gsc_seo",
  "ahrefs",
  "localo",
  "wordpress",
  "social",
  "knowledge",
  "content",
  "codex",
  "ga4",
  "merchant",
  "google_sheets"
]);

export const ActionStatusSchema = z.enum([
  "new",
  "ready",
  "needs_validation",
  "validation_failed",
  "ready_to_apply",
  "applying",
  "applied",
  "failed",
  "dismissed",
  "blocked"
]);

export const ActionValidationStatusSchema = z.enum([
  "not_validated",
  "valid",
  "invalid"
]);

export const ActionObjectSchema = z.object({
  id: z.string(),
  title: z.string(),
  domain: ActionDomainSchema,
  connector: z.string(),
  connector_label: z.string().default(""),
  mode: z.enum(["suggest", "prepare", "apply"]),
  mode_label: z.string().default(""),
  risk: z.enum(["low", "medium", "high", "critical"]),
  risk_label: z.string().default(""),
  status: ActionStatusSchema,
  status_label: z.string().default(""),
  evidence_ids: z.array(z.string()).min(1),
  evidence_summary_label: z.string().default(""),
  metrics: z.array(MetricFactSchema),
  human_diagnosis: z.string(),
  recommended_reason: z.string(),
  validation_status: ActionValidationStatusSchema,
  validation_status_label: z.string().default(""),
  review_gate: ActionReviewGateSchema.optional().default(DEFAULT_ACTION_REVIEW_GATE),
  preview_cards: z.array(ActionPreviewCardViewModelSchema).default([]),
  payload: z.record(z.string(), z.unknown()),
  audit_events: z.array(AuditEventSchema)
});

export const ActionValidationResultSchema = z.object({
  action_id: z.string(),
  valid: z.boolean(),
  status: z.enum(["valid", "invalid"]),
  status_label: z.string().default(""),
  errors: z.array(z.string()),
  warnings: z.array(z.string()),
  checked_at: z.string()
});

export const ActionMutationAuditRecordSchema = z.object({
  id: z.string(),
  action_id: z.string(),
  connector: z.string(),
  action_type: z.string().nullable().optional(),
  status: z.enum(["blocked", "applied", "failed"]),
  status_label: z.string().default(""),
  adapter_reached: z.boolean().default(false),
  external_write_attempted: z.boolean().default(false),
  mutation_attempted: z.boolean(),
  mutation_adapter: z.string().nullable().optional(),
  actor: z.string(),
  created_at: z.string(),
  audit_event_id: z.string(),
  evidence_ids: z.array(z.string()),
  blockers: z.array(z.string()),
  wordpress_draft_binding: ContentDraftRevisionBindingSchema.nullable().optional(),
  wordpress_revision_blockers: z.array(ActionWordPressDraftApplyBlockerSchema).default([]),
  summary: z.string(),
  redacted: z.boolean()
});

export const ActionMutationReadinessRequirementSchema = z.object({
  code: z.string(),
  label: z.string(),
  satisfied: z.boolean().default(false),
  evidence: z.string().nullable().optional()
});

export const ActionMutationReadinessBlockerSchema = z.object({
  code: z.string(),
  label: z.string(),
  reason: z.string(),
  next_step: z.string()
});

export const ActionMutationApplyContractSchema = z.object({
  contract: z.literal("action_apply_contract_v1"),
  action_id: z.string(),
  action_type: z.string(),
  connector: z.string(),
  allowed_operation: z.string(),
  required_mode: z.literal("apply").default("apply"),
  draft_only: z.boolean().default(true),
  publication_allowed: z.boolean().default(false),
  destructive_allowed: z.boolean().default(false),
  adapter_status: z.enum(["not_implemented", "implemented"]).default("not_implemented"),
  required_env_flags: z.array(z.string()).default([]),
  required_input_contracts: z.array(z.string()).default([]),
  required_audit_events: z.array(z.string()).default([]),
  blocked_outputs: z.array(z.string()).default([]),
  operator_summary: z.string()
});

export const ActionMutationReadinessResponseSchema = z.object({
  response_type: z.literal("action_mutation_readiness"),
  contract: z.literal("action_mutation_readiness_v1"),
  action_id: z.string(),
  title: z.string(),
  connector: z.string(),
  connector_label: z.string().default(""),
  mode: z.enum(["suggest", "prepare", "apply"]),
  mode_label: z.string().default(""),
  risk: z.enum(["low", "medium", "high", "critical"]),
  risk_label: z.string().default(""),
  validation_status: ActionValidationStatusSchema,
  review_gate_status: z.string().default(""),
  ready_to_request_apply: z.boolean().default(false),
  vendor_write_possible: z.boolean().default(false),
  would_attempt_vendor_write: z.boolean().default(false),
  mutation_adapter: z.string().nullable().optional(),
  apply_contract: ActionMutationApplyContractSchema.nullable().optional(),
  target_candidate_id: z.string().nullable().optional(),
  target_label: z.string().nullable().optional(),
  target_url: z.string().nullable().optional(),
  write_authorization_status: z
    .enum([
      "missing_audit_trace",
      "audit_actor_mismatch",
      "available",
      "blocked_outside_action_apply"
    ])
    .nullable()
    .optional(),
  missing_audit_event_types: z.array(z.string()).default([]),
  requirements: z.array(ActionMutationReadinessRequirementSchema).default([]),
  blockers: z.array(ActionMutationReadinessBlockerSchema).default([]),
  operator_next_step: z.string(),
  evidence_ids: z.array(z.string()).default([]),
  source_connectors: z.array(z.string()).default([]),
  latest_mutation_audit_id: z.string().nullable().optional(),
  latest_mutation_audit_status: z.enum(["blocked", "applied", "failed"]).nullable().optional()
});

export const ActionMutationReadinessSummaryResponseSchema = z.object({
  response_type: z.literal("action_mutation_readiness_summary"),
  contract: z.literal("action_mutation_readiness_summary_v1"),
  action_count: z.number().int().nonnegative().default(0),
  ready_to_request_apply_count: z.number().int().nonnegative().default(0),
  vendor_write_possible_count: z.number().int().nonnegative().default(0),
  would_attempt_vendor_write_count: z.number().int().nonnegative().default(0),
  prepare_only_count: z.number().int().nonnegative().default(0),
  missing_adapter_count: z.number().int().nonnegative().default(0),
  high_risk_blocked_count: z.number().int().nonnegative().default(0),
  top_blockers: z.array(z.string()).default([]),
  first_write_candidate: ActionMutationReadinessResponseSchema.nullable().optional(),
  first_write_candidate_reason: z.string().default(""),
  activation_plan_steps: z.array(z.string()).default([]),
  activation_next_step: z.string().default(""),
  operator_next_step: z.string(),
  items: z.array(ActionMutationReadinessResponseSchema).default([])
});

export const ActionApplyResultSchema = z.object({
  action_id: z.string(),
  applied: z.boolean(),
  status: z.enum(["applied", "blocked", "failed"]),
  status_label: z.string().default(""),
  audit_event: AuditEventSchema,
  mutation_audit: ActionMutationAuditRecordSchema,
  errors: z.array(z.string()),
  wordpress_revision_blockers: z.array(ActionWordPressDraftApplyBlockerSchema).default([]),
  adapter_result: z.record(z.string(), z.unknown()).nullable().optional()
});

export const ActionWordPressDraftApplyInputSchema = ContentDraftRevisionBindingSchema;

export const ActionPreviewRequestSchema = z.object({
  requested_by: z.string().min(1).nullable().optional(),
  max_items: z.number().int().min(1).max(50).optional(),
  wordpress_draft: ContentDraftRevisionBindingSchema.nullable().optional()
});

export const ActionPreviewResultSchema = z.object({
  action_id: z.string(),
  status: z.enum(["preview_ready", "blocked"]),
  status_label: z.string().default(""),
  dry_run: z.boolean(),
  mutation_allowed: z.boolean(),
  preview_contract: z.string().nullable().optional(),
  preview_items: z.array(ActionPreviewItemViewModelSchema),
  preview_cards: z.array(ActionPreviewCardViewModelSchema).default([]),
  preview_items_total: z.number(),
  omitted_items: z.number(),
  blockers: z.array(z.string()),
  blocker_labels: z.array(z.string()).default([]),
  audit_event: AuditEventSchema,
  review_gate: ActionReviewGateSchema
});

export const ActionReviewResultSchema = z.object({
  action_id: z.string(),
  status: z.enum(["recorded"]),
  status_label: z.string().default(""),
  audit_event: AuditEventSchema,
  review_gate: ActionReviewGateSchema
});

export const ActionConfirmRequestSchema = z.object({
  confirmed_by: z.string().min(1),
  notes: z.string().min(1).max(2000),
  preview_acknowledged: z.boolean().default(false),
  target_roas: z.number().positive().nullable().optional(),
  target_cpa_micros: z.number().int().positive().nullable().optional(),
  wordpress_draft: ContentDraftRevisionBindingSchema.nullable().optional()
});

export const ActionConfirmResultSchema = z.object({
  action_id: z.string(),
  confirmed: z.boolean(),
  status: z.enum(["confirmed", "blocked"]),
  status_label: z.string().default(""),
  blockers: z.array(z.string()),
  blocker_labels: z.array(z.string()).default([]),
  audit_event: AuditEventSchema,
  review_gate: ActionReviewGateSchema
});

export const ActionImpactCheckRequestSchema = z.object({
  checked_by: z.string().min(1),
  notes: z.string().min(1).max(2000),
  pre_window_days: z.number().int().min(1).max(90).optional(),
  post_window_days: z.number().int().min(1).max(90).optional(),
  wordpress_draft: ContentDraftRevisionBindingSchema.nullable().optional()
});

export const ActionImpactCheckResultSchema = z.object({
  action_id: z.string(),
  status: z.enum(["checked", "blocked"]),
  status_label: z.string().default(""),
  pre_window_days: z.number(),
  post_window_days: z.number(),
  metric_fact_count: z.number(),
  source_connectors: z.array(z.string()),
  source_connector_labels: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  blockers: z.array(z.string()),
  blocker_labels: z.array(z.string()).default([]),
  audit_event: AuditEventSchema,
  review_gate: ActionReviewGateSchema
});

export const ActionApplyRequestSchema = z.object({
  confirm: z.boolean(),
  confirmed_by: z.string().min(1),
  wordpress_draft: ActionWordPressDraftApplyInputSchema.optional()
});

export type ActionPreviewCardViewModel = z.infer<typeof ActionPreviewCardViewModelSchema>;
export type ActionObject = z.infer<typeof ActionObjectSchema>;
export type ActionValidationResult = z.infer<typeof ActionValidationResultSchema>;
export type ActionMutationAuditRecord = z.infer<typeof ActionMutationAuditRecordSchema>;
export type ActionMutationReadinessResponse = z.infer<typeof ActionMutationReadinessResponseSchema>;
export type ActionMutationReadinessSummaryResponse = z.infer<
  typeof ActionMutationReadinessSummaryResponseSchema
>;
export type ActionApplyResult = z.infer<typeof ActionApplyResultSchema>;
export type ContentDraftRevisionBinding = z.infer<typeof ContentDraftRevisionBindingSchema>;
export type ActionWordPressDraftApplyBlocker = z.infer<
  typeof ActionWordPressDraftApplyBlockerSchema
>;
export type ActionWordPressDraftApplyInput = z.infer<typeof ActionWordPressDraftApplyInputSchema>;
export type ActionPreviewRequest = z.infer<typeof ActionPreviewRequestSchema>;
export type ActionPreviewResult = z.infer<typeof ActionPreviewResultSchema>;
export type ActionReviewRequest = z.infer<typeof ActionReviewRequestSchema>;
export type ActionReviewResult = z.infer<typeof ActionReviewResultSchema>;
export type ActionConfirmRequest = z.infer<typeof ActionConfirmRequestSchema>;
export type ActionConfirmResult = z.infer<typeof ActionConfirmResultSchema>;
export type ActionImpactCheckRequest = z.infer<typeof ActionImpactCheckRequestSchema>;
export type ActionImpactCheckResult = z.infer<typeof ActionImpactCheckResultSchema>;
export type ActionApplyRequest = z.infer<typeof ActionApplyRequestSchema>;
