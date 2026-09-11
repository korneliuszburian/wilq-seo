import { z } from "zod";

import {
  ContentDocumentWorkspaceSchema,
  ContentDraftRevisionReviewSchema,
  ContentDraftRevisionSchema,
  ContentWorkflowOperatorJourneySchema
} from "./contentWorkflow";

const ContentProductionSha256Schema = z.string().regex(/^[0-9a-f]{64}$/);

export const ContentProductionDecisionBlockerSchema = z.object({
  code: z.string().min(1),
  owner: z.string().min(1),
  next_step_pl: z.string().min(1),
  sources: z.array(z.string().min(1)).min(1),
  blocks_initial_generation: z.literal(true)
}).strict();

export const ContentProductionDecisionFreshnessSchema = z.object({
  state: z.string().min(1),
  checked_at: z.string().min(1),
  requires_refresh: z.boolean(),
  connector_ids: z.array(z.string())
}).strict();

export const ContentProductionRevisionBindingSchema = z.object({
  current_work_item_id: z.string().min(1),
  retained_work_item_id: z.string().min(1).nullable(),
  revision_work_item_id: z.string().min(1).nullable(),
  identity_reconciliation_status: z.enum(["fork", "retained_missing"]),
  revision_id: z.string().min(1),
  revision_digest: ContentProductionSha256Schema,
  verified_draft_action_ids: z.array(z.string().min(1)),
  verified_draft_post_ids: z.array(z.string().min(1)),
  must_not_regenerate: z.literal(true)
}).strict().superRefine((binding, context) => {
  if (new Set(binding.verified_draft_action_ids).size !== binding.verified_draft_action_ids.length) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["verified_draft_action_ids"],
      message: "Verified draft action IDs must be unique."
    });
  }
  if (new Set(binding.verified_draft_post_ids).size !== binding.verified_draft_post_ids.length) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["verified_draft_post_ids"],
      message: "Verified draft post IDs must be unique."
    });
  }
  if (
    binding.identity_reconciliation_status === "fork" &&
    (binding.retained_work_item_id === null ||
      binding.revision_work_item_id !== binding.retained_work_item_id ||
      binding.retained_work_item_id === binding.current_work_item_id)
  ) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["revision_work_item_id"],
      message: "Fork revision owner must be the exact retained work item."
    });
  }
  if (
    binding.identity_reconciliation_status === "retained_missing" &&
    (binding.retained_work_item_id !== null ||
      binding.revision_work_item_id === binding.current_work_item_id)
  ) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["retained_work_item_id"],
      message: "Retained-missing binding requires a distinct historical owner."
    });
  }
});

export const ContentReusableDocumentReadySchema = z.object({
  status: z.literal("ready"),
  revision: z.lazy(() => ContentDraftRevisionSchema),
  review: z.lazy(() => ContentDraftRevisionReviewSchema)
}).strict().superRefine((document, context) => {
  if (document.review.decision !== "approved") {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["review", "decision"],
      message: "Reusable document requires an approved review."
    });
  }
  if (
    document.review.work_item_id !== document.revision.work_item_id ||
    document.review.revision_id !== document.revision.revision_id ||
    document.review.revision_digest !== document.revision.content_digest
  ) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["review"],
      message: "Reusable document review must match the exact revision."
    });
  }
});

export const ContentReusableDocumentBlockedSchema = z.object({
  status: z.literal("blocked"),
  code: z.enum([
    "missing_revision_owner",
    "latest_revision_missing",
    "latest_revision_drift",
    "latest_review_missing",
    "latest_review_not_approved",
    "latest_review_mismatch"
  ]),
  reason_pl: z.string().min(1),
  safe_next_step_pl: z.string().min(1)
}).strict();

export const ContentReusableDocumentSchema = z.discriminatedUnion("status", [
  ContentReusableDocumentReadySchema,
  ContentReusableDocumentBlockedSchema
]);

const ContentProductionDecisionAvailableBaseSchema = z.object({
  status: z.literal("available"),
  run_id: z.string().min(1),
  run_digest: ContentProductionSha256Schema,
  decision_set_digest: ContentProductionSha256Schema,
  generation_allowed: z.literal(false),
  lookup_basis: z.enum(["current", "retained", "historical_action_owner"]),
  canonical_path: z.string().min(1),
  public_url: z.string().url(),
  current_work_item_id: z.string().min(1).nullable(),
  retained_work_item_id: z.string().min(1).nullable(),
  reason_pl: z.string().min(1),
  safe_next_step_pl: z.string().min(1),
  blockers: z.array(ContentProductionDecisionBlockerSchema),
  primary_evidence_ids: z.array(z.string().min(1)).min(1),
  lineage_evidence_ids: z.array(z.string().min(1)),
  source_connectors: z.array(z.string().min(1)).min(1),
  freshness: ContentProductionDecisionFreshnessSchema
}).strict();

export const ContentProductionDecisionReuseSchema =
  ContentProductionDecisionAvailableBaseSchema.extend({
    decision: z.literal("reuse"),
    revision_binding: ContentProductionRevisionBindingSchema,
    reusable_document: ContentReusableDocumentSchema
  }).superRefine((decision, context) => {
    const binding = decision.revision_binding;
    if (
      decision.current_work_item_id !== binding.current_work_item_id ||
      decision.retained_work_item_id !== binding.retained_work_item_id
    ) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["revision_binding"],
        message: "Production identities must match the reusable revision binding."
      });
    }
    const reusable = decision.reusable_document;
    if (reusable.status === "ready") {
      if (
        binding.revision_work_item_id === null ||
        reusable.revision.work_item_id !== binding.revision_work_item_id ||
        reusable.revision.revision_id !== binding.revision_id ||
        reusable.revision.content_digest !== binding.revision_digest ||
        reusable.review.work_item_id !== binding.revision_work_item_id ||
        reusable.review.revision_id !== binding.revision_id ||
        reusable.review.revision_digest !== binding.revision_digest
      ) {
        context.addIssue({
          code: z.ZodIssueCode.custom,
          path: ["reusable_document"],
          message: "Reusable document does not match its production binding."
        });
      }
    } else if (
      (binding.revision_work_item_id === null) !==
      (reusable.code === "missing_revision_owner")
    ) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["reusable_document", "code"],
        message: "Missing revision owner must use its exact reusable blocker."
      });
    }
  });

export const ContentProductionDecisionRefreshSchema =
  ContentProductionDecisionAvailableBaseSchema.extend({
    decision: z.literal("refresh"),
    blockers: z.array(ContentProductionDecisionBlockerSchema).min(1)
  });
export const ContentProductionDecisionWriteSchema =
  ContentProductionDecisionAvailableBaseSchema.extend({ decision: z.literal("write") });
export const ContentProductionDecisionBlockedSchema =
  ContentProductionDecisionAvailableBaseSchema.extend({
    decision: z.literal("blocked"),
    blockers: z.array(ContentProductionDecisionBlockerSchema).min(1)
  });

export const ContentProductionDecisionAvailableSchema = z.discriminatedUnion("decision", [
  ContentProductionDecisionReuseSchema,
  ContentProductionDecisionRefreshSchema,
  ContentProductionDecisionWriteSchema,
  ContentProductionDecisionBlockedSchema
]);

export const ContentProductionDecisionMissingSchema = z.object({
  status: z.literal("missing")
}).strict();

export const ContentProductionDecisionSchema = z.discriminatedUnion("status", [
  ContentProductionDecisionMissingSchema,
  ContentProductionDecisionAvailableSchema
]);

export const ContentSelectedWorkspaceSchema = z
  .object({
    response_type: z.literal("content_selected_workspace").default("content_selected_workspace"),
    contract_version: z.literal("content_selected_workspace_v2").default("content_selected_workspace_v2"),
    status: z.enum(["ready", "missing"]),
    work_item_id: z.string().min(1),
    requested_work_item_id: z.string().min(1),
    production_decision: ContentProductionDecisionSchema,
    operator_journey: z.lazy(() => ContentWorkflowOperatorJourneySchema),
    workspace: ContentDocumentWorkspaceSchema.nullable().optional(),
    reason: z.string().min(1),
    safe_next_step: z.string().min(1)
  })
  .strict()
  .superRefine((value, context) => {
    if (value.status === "ready" && !value.workspace) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Ready workspace requires exact workspace data."
      });
    }
    if (value.status === "missing" && value.workspace) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Missing workspace cannot carry workspace data."
      });
    }
    if (value.workspace && value.workspace.work_item_id !== value.work_item_id) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Workspace must match the selected work item."
      });
    }
    if (
      value.workspace?.canonical_document.revision &&
      value.workspace.canonical_document.revision.work_item_id !== value.work_item_id
    ) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["workspace", "canonical_document", "revision", "work_item_id"],
        message: "Current canonical document must match the selected work item."
      });
    }
    const production = value.production_decision;
    if (production.status === "missing") {
      if (value.requested_work_item_id !== value.work_item_id) {
        context.addIssue({
          code: z.ZodIssueCode.custom,
          path: ["requested_work_item_id"],
          message: "Unclassified workspace must preserve its requested identity."
        });
      }
      return;
    }
    if (value.status !== "ready" || !value.workspace) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["production_decision"],
        message: "Available production decision requires a ready current workspace."
      });
      return;
    }
    const expectedWorkItemId = production.current_work_item_id ?? value.requested_work_item_id;
    if (value.work_item_id !== expectedWorkItemId) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["work_item_id"],
        message: "Selected workspace must use the current production identity."
      });
    }
    const lookupMatches = production.lookup_basis === "current"
      ? value.requested_work_item_id === production.current_work_item_id
      : production.lookup_basis === "retained"
        ? value.requested_work_item_id === production.retained_work_item_id
        : production.decision === "reuse" &&
          production.revision_binding.identity_reconciliation_status === "retained_missing" &&
          value.requested_work_item_id === production.revision_binding.revision_work_item_id;
    if (!lookupMatches) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["production_decision", "lookup_basis"],
        message: "Production lookup basis does not match the requested identity."
      });
    }
    if (value.workspace.next_action.kind !== "none") {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["workspace", "next_action", "kind"],
        message: "Generation-disabled production decision requires no workspace action."
      });
    }
    const blockedReusableDocument =
      production.decision === "reuse" && production.reusable_document.status === "blocked"
        ? production.reusable_document
        : null;
    const expectedReason = blockedReusableDocument?.reason_pl ?? production.reason_pl;
    const expectedSafeNextStep =
      blockedReusableDocument?.safe_next_step_pl ?? production.safe_next_step_pl;
    if (value.reason !== expectedReason) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["reason"],
        message: "Selected workspace must expose the current production reason."
      });
    }
    if (value.workspace.next_action.reason !== expectedReason) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["workspace", "next_action", "reason"],
        message: "Disabled workspace action must explain the production decision."
      });
    }
    if (value.safe_next_step !== expectedSafeNextStep) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["safe_next_step"],
        message: "Selected workspace must expose the production safe next step."
      });
    }
  });

export type ContentProductionDecision = z.infer<typeof ContentProductionDecisionSchema>;
export type ContentProductionRevisionBinding = z.infer<
  typeof ContentProductionRevisionBindingSchema
>;
export type ContentReusableDocument = z.infer<typeof ContentReusableDocumentSchema>;
export type ContentSelectedWorkspace = z.infer<typeof ContentSelectedWorkspaceSchema>;
