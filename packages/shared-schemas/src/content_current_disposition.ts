import { z } from "zod";

import { ActionObjectSchema } from "./actions";

const ContentCurrentDispositionDigestSchema = z.string().regex(/^[0-9a-f]{64}$/);

export const ContentCurrentDispositionSnapshotSchema = z
  .object({
    schema_version: z.literal("wilq_current_disposition_snapshot_v1"),
    current_work_item_id: z.string().min(1),
    canonical_path: z.string().min(1),
    public_url: z.string().min(1),
    classification_run_id: z.string().min(1),
    classification_run_digest: ContentCurrentDispositionDigestSchema,
    classification_decision_set_digest: ContentCurrentDispositionDigestSchema,
    classification_source_row_digest: ContentCurrentDispositionDigestSchema,
    evidence_ids: z.array(z.string().min(1)).min(1),
    proposed_final_disposition: z.enum(["keep", "noindex", "redirect", "remove"]),
    context_digest: ContentCurrentDispositionDigestSchema
  })
  .strict();

export const ContentCurrentDispositionReceiptSchema = z
  .object({
    receipt_id: z.string().min(1),
    receipt_digest: ContentCurrentDispositionDigestSchema,
    action_id: z.string().min(1),
    action_payload_digest: ContentCurrentDispositionDigestSchema,
    authority_snapshot: ContentCurrentDispositionSnapshotSchema,
    preview_audit_id: z.string().min(1),
    review_audit_id: z.string().min(1),
    confirmation_audit_id: z.string().min(1),
    impact_audit_id: z.string().min(1),
    reviewed_by: z.string().min(1),
    confirmed_by: z.string().min(1)
  })
  .strict();

export const ContentCurrentDispositionBlockerSchema = z
  .object({
    seam: z.enum(["classification", "current_context", "receipt"]),
    reason: z.string().min(1),
    evidence_ids: z.array(z.string().min(1)).default([]),
    next_step: z.string().min(1)
  })
  .strict();

export const ContentCurrentDispositionReadProjectionSchema = z
  .object({
    status: z.enum(["missing", "preview_ready", "blocked", "current"]),
    action: ActionObjectSchema.nullable(),
    receipt: ContentCurrentDispositionReceiptSchema.nullable(),
    blockers: z.array(ContentCurrentDispositionBlockerSchema).default([]),
    safe_next_step: z.string().min(1)
  })
  .strict();

export const ContentCurrentDispositionApprovalRequestSchema = z
  .object({
    expected_snapshot_digest: ContentCurrentDispositionDigestSchema,
    expected_action_payload_digest: ContentCurrentDispositionDigestSchema,
    expected_preview_audit_id: z.string().min(1).max(240),
    confirm: z.literal(true),
    notes: z.string().min(1).max(2000)
  })
  .strict();

const ContentCurrentDispositionApprovalCommonSchema = z.object({
  projection: ContentCurrentDispositionReadProjectionSchema,
  safe_next_step: z.string().min(1),
  audit_ids: z.record(z.string(), z.string()).default({}),
  external_write_attempted: z.literal(false)
});

export const ContentCurrentDispositionApprovalCurrentResponseSchema =
  ContentCurrentDispositionApprovalCommonSchema.extend({
    status: z.literal("current"),
    action: ActionObjectSchema,
    receipt: ContentCurrentDispositionReceiptSchema,
    blockers: z.array(ContentCurrentDispositionBlockerSchema).default([])
  }).superRefine((value, context) => {
    if (value.projection.status !== "current") {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["projection", "status"],
        message: "Current approval requires a current projection."
      });
    }
  });

export const ContentCurrentDispositionApprovalBlockedResponseSchema =
  ContentCurrentDispositionApprovalCommonSchema.extend({
    status: z.literal("blocked"),
    action: ActionObjectSchema.nullable(),
    receipt: ContentCurrentDispositionReceiptSchema.nullable(),
    blockers: z.array(ContentCurrentDispositionBlockerSchema).min(1)
  }).superRefine((value, context) => {
    if (value.projection.status !== "blocked") {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["projection", "status"],
        message: "Blocked approval requires a blocked projection."
      });
    }
  });

export const ContentCurrentDispositionApprovalResponseSchema = z.discriminatedUnion("status", [
  ContentCurrentDispositionApprovalCurrentResponseSchema,
  ContentCurrentDispositionApprovalBlockedResponseSchema
]);

export type ContentCurrentDispositionSnapshot = z.infer<
  typeof ContentCurrentDispositionSnapshotSchema
>;
export type ContentCurrentDispositionReceipt = z.infer<
  typeof ContentCurrentDispositionReceiptSchema
>;
export type ContentCurrentDispositionBlocker = z.infer<
  typeof ContentCurrentDispositionBlockerSchema
>;
export type ContentCurrentDispositionReadProjection = z.infer<
  typeof ContentCurrentDispositionReadProjectionSchema
>;
export type ContentCurrentDispositionApprovalRequest = z.infer<
  typeof ContentCurrentDispositionApprovalRequestSchema
>;
export type ContentCurrentDispositionApprovalCurrentResponse = z.infer<
  typeof ContentCurrentDispositionApprovalCurrentResponseSchema
>;
export type ContentCurrentDispositionApprovalBlockedResponse = z.infer<
  typeof ContentCurrentDispositionApprovalBlockedResponseSchema
>;
export type ContentCurrentDispositionApprovalResponse = z.infer<
  typeof ContentCurrentDispositionApprovalResponseSchema
>;
