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
