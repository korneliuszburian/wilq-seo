import { z } from "zod";

import { ActionObjectSchema } from "./actions";
import { ConnectorStatusSchema, EvidenceSchema } from "./connectors";
import { SocialHistoryInventorySchema } from "./social_history";

export const SocialDraftContextSchema = z.object({
  mode: z.literal("review_only"),
  publish_allowed: z.literal(false),
  missing_publish_access: z.record(z.string(), z.array(z.string())),
  draft_action_ids: z.array(z.string()),
  source_inputs: z.array(z.record(z.string(), z.unknown())),
  draft_constraints: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  source_metric_names: z.array(z.string()).optional(),
  source_connectors: z.array(z.string()).optional(),
  evidence_ids: z.array(z.string()).optional(),
  historical_social_inventory_status: z.enum(["missing", "invalid", "review_ready"]),
  historical_social_inventory_status_label: z.string(),
  duplicate_risk_status: z.literal("blocked_until_social_history_review"),
  duplicate_risk_status_label: z.string(),
  required_history_sources: z.array(z.enum(["linkedin", "facebook"])),
  missing_history_evidence: z.array(z.string()),
  social_history_inventory: SocialHistoryInventorySchema,
  history_audit_endpoint: z.literal("/api/social/history-inventory/audit"),
  history_audit_contract: z.literal("social_history_inventory_v1"),
  operator_next_step: z.string()
});

export const SocialPublisherContextPackSchema = z.object({
  strict_instruction: z.string(),
  connector_status: z.array(ConnectorStatusSchema),
  active_action_objects: z.array(ActionObjectSchema),
  evidence_summaries: z.array(EvidenceSchema),
  social_draft_context: SocialDraftContextSchema
});

export const SocialReuseProposalSchema = z.object({
  contract: z.literal("social_reuse_proposal_v1"),
  proposal_id: z.string().min(1),
  work_item_id: z.string().min(1),
  platform: z.enum(["linkedin", "facebook"]),
  source_revision_id: z.string().min(1),
  source_revision_digest: z.string().regex(/^[0-9a-f]{64}$/),
  source_evidence_ids: z.array(z.string().min(1)).min(1),
  source_claim_ids: z.array(z.string().min(1)),
  audience: z.string().min(1),
  angle: z.string().min(1),
  body: z.string().min(1),
  constraints: z.array(z.string().min(1)).min(1),
  duplicate_risk_inventory_digest: z.string().regex(/^[0-9a-f]{64}$/),
  duplicate_risk_status: z.literal("review_ready"),
  measurement_hypothesis: z.string().min(1),
  status: z.enum(["review_required", "approved", "rejected", "stale", "blocked"]),
  publish_allowed: z.literal(false),
  created_at: z.string(),
  proposal_digest: z.string().regex(/^[0-9a-f]{64}$/)
});

export const SocialReuseProposalResponseSchema = z.object({
  status: z.enum(["created", "blocked", "stale"]),
  proposal: SocialReuseProposalSchema.optional(),
  review: z.object({
    contract: z.literal("social_reuse_review_v1"),
    review_id: z.string().min(1),
    proposal_id: z.string().min(1),
    proposal_digest: z.string().regex(/^[0-9a-f]{64}$/),
    review_number: z.number().int().positive(),
    decision: z.enum(["approved", "needs_changes", "rejected"]),
    reviewed_by: z.string().min(1),
    notes: z.string(),
    checked_items: z.array(z.string().min(1)).min(1),
    evidence_ids: z.array(z.string().min(1)).min(1),
    created_at: z.string()
  }).optional(),
  blocker: z.string().nullable().optional(),
  next_step: z.string().min(1)
});

export const SocialReuseReviewResponseSchema = z.object({
  status: z.enum(["recorded", "idempotent", "blocked", "stale"]),
  proposal: SocialReuseProposalSchema.optional(),
  review: z.object({
    contract: z.literal("social_reuse_review_v1"),
    review_id: z.string().min(1),
    proposal_id: z.string().min(1),
    proposal_digest: z.string().regex(/^[0-9a-f]{64}$/),
    review_number: z.number().int().positive(),
    decision: z.enum(["approved", "needs_changes", "rejected"]),
    reviewed_by: z.string().min(1),
    notes: z.string(),
    checked_items: z.array(z.string().min(1)).min(1),
    evidence_ids: z.array(z.string().min(1)).min(1),
    created_at: z.string()
  }).optional(),
  blocker: z.string().nullable().optional(),
  next_step: z.string().min(1)
});
