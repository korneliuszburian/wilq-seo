import { z } from "zod";

import { codePointBoundedString, isSortedAndUnique } from "./content_intake";

export const ContentBriefFieldSchema = z.strictObject({
  field: codePointBoundedString(1, 120),
  value: codePointBoundedString(1, 2000),
  provenance: z.enum(["user_input", "evidence", "inference", "unknown"]),
  detail: codePointBoundedString(1, 600),
  evidence_ids: z.array(z.string()).default([])
}).refine(
  (field) => isSortedAndUnique(field.evidence_ids),
  {
    path: ["evidence_ids"],
    message: "Brief field evidence IDs must be sorted and unique."
  }
);

export const ContentBriefBlockerSchema = z.strictObject({
  code: codePointBoundedString(1, 160),
  owner: codePointBoundedString(1, 160),
  detail: codePointBoundedString(1, 600)
});

export const ContentBriefProposalSchema = z.strictObject({
  schema_version: z.literal("wilq_content_brief_proposal_v1").default("wilq_content_brief_proposal_v1"),
  queue_id: codePointBoundedString(1, 240),
  status: z.enum(["ready", "blocked"]),
  route: z.enum(["existing_page", "new_page", "ambiguous"]).nullable().default(null),
  target_work_item_id: codePointBoundedString(0, 240).nullable().default(null),
  target_path: codePointBoundedString(0, 2048).nullable().default(null),
  target_public_url: codePointBoundedString(0, 2048).nullable().default(null),
  fields: z.array(ContentBriefFieldSchema).min(1),
  blockers: z.array(ContentBriefBlockerSchema).default([]),
  workflow_step: z.string().min(1),
  research_status: z.string().nullable().default(null),
  planning_proposal_created: z.literal(false).default(false),
  action_created: z.literal(false).default(false),
  generation_allowed: z.literal(false).default(false),
  safe_next_step: codePointBoundedString(1, 600)
}).superRefine((brief, context) => {
  if (brief.status === "ready" && (brief.route === null || brief.blockers.length > 0)) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["status"],
      message: "A ready brief needs one route and no blockers."
    });
  }
  if (brief.status === "blocked" && brief.blockers.length === 0) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["blockers"],
      message: "A blocked brief needs at least one typed blocker."
    });
  }
  if (new Set(brief.fields.map((field) => field.field)).size !== brief.fields.length) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["fields"],
      message: "Brief fields must be unique."
    });
  }
  if (new Set(brief.blockers.map((blocker) => blocker.code)).size !== brief.blockers.length) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["blockers"],
      message: "Brief blockers must be unique."
    });
  }
  if (brief.route === "existing_page" && (!brief.target_work_item_id || !brief.target_path)) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["target_work_item_id"],
      message: "The existing-page route needs its exact target."
    });
  }
});

export type ContentBriefProposal = z.infer<typeof ContentBriefProposalSchema>;
export type ContentBriefField = z.infer<typeof ContentBriefFieldSchema>;
export type ContentBriefBlocker = z.infer<typeof ContentBriefBlockerSchema>;
