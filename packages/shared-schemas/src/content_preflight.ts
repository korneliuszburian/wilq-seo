import { z } from "zod";

export const ContentPreflightItemSchema = z.object({
  id: z.string(),
  technical_decision_id: z.string(),
  recommended_mode: z.enum(["preserve", "refresh", "merge", "create", "block"]),
  recommended_mode_label: z.string().default(""),
  status: z.enum(["allowed", "review_required", "blocked"]),
  status_label: z.string().default(""),
  create_allowed: z.boolean(),
  draft_allowed: z.boolean(),
  wordpress_draft_allowed: z.boolean(),
  sales_brief_allowed: z.boolean(),
  source_public_url: z.string().nullable().optional(),
  preview_url: z.string().nullable().optional(),
  intended_final_url: z.string().nullable().optional(),
  final_canonical_url: z.string().nullable().optional(),
  inventory_gate_status: z.string().nullable().optional(),
  inventory_gate_status_label: z.string().nullable().optional(),
  canonical_gate_status: z.string().nullable().optional(),
  canonical_gate_status_label: z.string().nullable().optional(),
  duplicate_gate_status: z.string().nullable().optional(),
  duplicate_gate_status_label: z.string().nullable().optional(),
  claim_gate_status: z.string(),
  claim_gate_status_label: z.string().default(""),
  service_fit_status: z.string(),
  service_fit_status_label: z.string().default(""),
  similar_existing_urls: z.array(z.string()),
  query_overlap_summary: z.string(),
  blocked_claims: z.array(z.string()),
  missing_inputs: z.array(z.string()),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  source_connectors: z.array(z.string()),
  source_connector_labels: z.array(z.string()).default([]),
  next_step: z.string()
});

export const ContentPreflightResponseSchema = z.object({
  generated_at: z.string().nullable().optional(),
  language: z.literal("pl-PL"),
  strict_instruction: z.string(),
  primary_item: ContentPreflightItemSchema.nullable().optional(),
  items: z.array(ContentPreflightItemSchema),
  evidence_ids: z.array(z.string()),
  source_connectors: z.array(z.string()),
  source_connector_labels: z.array(z.string()).default([]),
  blocker_count: z.number()
});

