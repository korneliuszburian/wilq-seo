import { z } from "zod";

const MaterialReviewActionCommonSchema = z.object({
  response_type: z.literal("content_material_review_action_v2"),
  external_write_attempted: z.literal(false),
  generation_allowed: z.literal(false)
});

export const ContentMaterialReviewActionReadySchema = MaterialReviewActionCommonSchema.extend({
  status: z.literal("preview_ready"),
  action_id: z.string().min(1)
});

export const ContentMaterialReviewActionBlockedSchema = MaterialReviewActionCommonSchema.extend({
  status: z.literal("blocked"),
  blocker_code: z.enum([
    "material_review_work_item_missing",
    "material_review_source_stale",
    "material_review_context_invalid",
    "material_review_source_unavailable"
  ]),
  blocker_owner: z.string().min(1),
  safe_next_step: z.string().min(1)
});

export const ContentMaterialReviewActionResponseSchema = z.discriminatedUnion("status", [
  ContentMaterialReviewActionReadySchema,
  ContentMaterialReviewActionBlockedSchema
]);

export type ContentMaterialReviewActionResponse = z.infer<
  typeof ContentMaterialReviewActionResponseSchema
>;

const CurrentMaterialTextCommonSchema = z.object({
  response_type: z.literal("current_material_text_v1"),
  is_generated: z.literal(false),
  evidence_ids: z.array(z.string().min(1))
});

export const CurrentMaterialTextExactSchema = CurrentMaterialTextCommonSchema.extend({
  status: z.literal("exact"),
  action_id: z.string().min(1),
  preview_id: z.string().min(1),
  preview_digest: z.string().regex(/^[0-9a-f]{64}$/),
  source_url: z.string().url(),
  title: z.string(),
  text: z.string().min(1),
  body_digest: z.string().regex(/^[0-9a-f]{64}$/),
  read_at: z.string().min(1)
});

export const CurrentMaterialTextBlockedSchema = CurrentMaterialTextCommonSchema.extend({
  status: z.literal("blocked"),
  blocker_code: z.enum(["material_review_text_changed", "material_review_text_unavailable"]),
  blocker_owner: z.string().min(1),
  safe_next_step: z.string().min(1)
});

export const CurrentMaterialTextResponseSchema = z.discriminatedUnion("status", [
  CurrentMaterialTextExactSchema,
  CurrentMaterialTextBlockedSchema
]);

export type CurrentMaterialTextResponse = z.infer<typeof CurrentMaterialTextResponseSchema>;
