import { z } from "zod";

import { ActionObjectSchema } from "./actions";
import { codePointBoundedString } from "./content_intake";
import {
  ResearchPacketV3BlockerSchema,
  ResearchPacketV3InternalLinkSchema,
  ResearchPacketV3LegalRequirementSchema,
  ResearchPacketV3PlanningContextSchema
} from "./content_research_packet_v3_action";

const Hex64Schema = z.string().regex(/^[0-9a-f]{64}$/);

export const PlanningGenerationIntentV3SnapshotSchema = z.strictObject({
  schema_version: z.literal("wilq_planning_generation_intent_snapshot_v3"),
  intent_digest: Hex64Schema,
  context_digest: Hex64Schema,
  approval_receipt_digest: Hex64Schema,
  approval_action_id: codePointBoundedString(1, 240),
  work_item_id: codePointBoundedString(1, 240),
  packet_id: codePointBoundedString(1, 240),
  packet_digest: Hex64Schema,
  content_kind: z.enum(["service", "editorial"]).nullable().default(null),
  service_card_id: codePointBoundedString(1, 240).nullable().default(null),
  page_url: codePointBoundedString(1, 2048),
  canonical_path: codePointBoundedString(1, 2048),
  identity_digest: Hex64Schema,
  per_url_delivery_identity_action_id: codePointBoundedString(1, 240).nullable().default(null),
  material_meaning_digest: Hex64Schema,
  source_pack_id: codePointBoundedString(1, 240),
  source_pack_hash: Hex64Schema,
  selected_fact_ids: z.array(z.string()).min(1).max(256),
  evidence_ids: z.array(z.string()).min(1).max(512),
  planning_context: ResearchPacketV3PlanningContextSchema,
  cta_direction: z.string().min(1),
  minimum_cta_blocks: z.number().int().min(1).max(4),
  required_cta_patterns: z.array(z.string()).default([]),
  internal_links: z.array(ResearchPacketV3InternalLinkSchema).min(1),
  regulatory_profile_id: codePointBoundedString(1, 240),
  regulatory_profile_version: codePointBoundedString(1, 120),
  legal_requirements: z.array(ResearchPacketV3LegalRequirementSchema).min(1),
  generation_performed: z.literal(false).default(false),
  model_enqueued: z.literal(false).default(false),
  external_write_attempted: z.literal(false).default(false)
});

export const PlanningGenerationIntentV3ReadySchema = z.strictObject({
  response_type: z.literal("planning_generation_intent_v3"),
  status: z.literal("preview_ready"),
  action_id: codePointBoundedString(1, 240),
  action: ActionObjectSchema,
  snapshot: PlanningGenerationIntentV3SnapshotSchema,
  generation_performed: z.literal(false).default(false),
  model_enqueued: z.literal(false).default(false),
  external_write_attempted: z.literal(false).default(false)
});

export const PlanningGenerationIntentV3BlockedSchema = z.strictObject({
  response_type: z.literal("planning_generation_intent_v3"),
  status: z.literal("blocked"),
  work_item_id: codePointBoundedString(1, 240),
  blocker_code: codePointBoundedString(1, 160),
  blocker_owner: codePointBoundedString(1, 160),
  evidence_ids: z.array(z.string()).default([]),
  safe_next_step: codePointBoundedString(1, 600),
  generation_performed: z.literal(false).default(false),
  model_enqueued: z.literal(false).default(false),
  external_write_attempted: z.literal(false).default(false)
});

export const PlanningGenerationIntentV3ResponseSchema = z.discriminatedUnion("status", [
  PlanningGenerationIntentV3ReadySchema,
  PlanningGenerationIntentV3BlockedSchema
]);

export const PlanningGenerationIntentV3DispatchOutcomeSchema = z.strictObject({
  response_type: z.literal("planning_generation_intent_v3_dispatch"),
  status: z.enum(["accepted", "blocked"]),
  action_id: codePointBoundedString(1, 240),
  work_item_id: z.string().nullable().default(null),
  intent_receipt_id: z.string().nullable().default(null),
  planning_input_digest: Hex64Schema.nullable().default(null),
  proposal_status: z.string().nullable().default(null),
  blocker: ResearchPacketV3BlockerSchema.nullable().default(null),
  safe_next_step: codePointBoundedString(1, 600),
  generation_performed: z.literal(false).default(false),
  external_write_attempted: z.literal(false).default(false)
}).superRefine((outcome, context) => {
  if (
    outcome.status === "accepted"
    && (outcome.blocker !== null || !outcome.intent_receipt_id?.trim())
  ) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["intent_receipt_id"],
      message: "Accepted v3 dispatch requires its exact local intent receipt."
    });
  }
  if (outcome.status === "blocked" && outcome.blocker === null) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["blocker"],
      message: "Blocked v3 dispatch requires a typed blocker."
    });
  }
});

export type PlanningGenerationIntentV3Snapshot = z.infer<
  typeof PlanningGenerationIntentV3SnapshotSchema
>;
export type PlanningGenerationIntentV3Response = z.infer<
  typeof PlanningGenerationIntentV3ResponseSchema
>;
export type PlanningGenerationIntentV3DispatchOutcome = z.infer<
  typeof PlanningGenerationIntentV3DispatchOutcomeSchema
>;
