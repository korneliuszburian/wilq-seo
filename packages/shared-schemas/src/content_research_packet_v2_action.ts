import { z } from "zod";

const DigestSchema = z.string().regex(/^[0-9a-f]{64}$/);

export const ResearchPacketV2PreviewRecordSchema = z.object({
  schema_version: z.literal("wilq_research_packet_v2_preview_record_v1"),
  preview_hash: DigestSchema,
  work_item_id: z.string().min(1),
  snapshot: z.object({
    status: z.literal("ready"),
    work_item_id: z.string().min(1),
    preview_hash: DigestSchema,
    source_pack_hash: DigestSchema,
    selected_facts: z.array(z.object({
      source_fact_id: z.string().min(1),
      text: z.string().min(1),
      source_reference: z.string().min(1),
      freshness_date: z.string().min(1),
      source_type: z.string().min(1),
      source_connectors: z.array(z.string().min(1)).min(1),
      fact_digest: DigestSchema,
      evidence_ids: z.array(z.string().min(1)).min(1)
    })).min(1),
    planning_context: z.object({
      target_reader: z.string().min(1),
      buyer_problem: z.string().min(1),
      buyer_trigger: z.string().min(1),
      search_intent: z.string().min(1)
    }),
    cta_direction: z.string().nullable().optional(),
    minimum_cta_blocks: z.number().int().min(1).max(4).nullable().optional(),
    required_cta_patterns: z.array(z.string().min(1)).optional(),
    internal_links: z.array(z.object({
      target_url: z.string().min(1),
      anchor_hint: z.string().min(1),
      evidence_ids: z.array(z.string().min(1)).min(1)
    })),
    legal_requirements: z.array(z.object({
      requirement_id: z.string().min(1),
      label: z.string().min(1),
      source_fact_ids: z.array(z.string().min(1)).min(1),
      evidence_ids: z.array(z.string().min(1)).min(1)
    })),
    regulatory_profile_id: z.string().nullable().optional(),
    regulatory_profile_version: z.string().nullable().optional(),
    evidence_ids: z.array(z.string().min(1)).min(1),
    generation_allowed: z.literal(false),
    packet_write_allowed: z.literal(false)
  })
}).superRefine((record, context) => {
  if (record.work_item_id !== record.snapshot.work_item_id ||
      record.preview_hash !== record.snapshot.preview_hash) {
    context.addIssue({ code: "custom", message: "Packet preview identity mismatch" });
  }
});

const CommonActionResponse = z.object({
  response_type: z.literal("research_packet_v2_action"),
  external_write_attempted: z.literal(false),
  generation_allowed: z.literal(false)
});

export const ResearchPacketV2ActionReadySchema = CommonActionResponse.extend({
  status: z.literal("preview_ready"),
  action_id: z.string().min(1)
});

export const ResearchPacketV2ActionBlockedSchema = CommonActionResponse.extend({
  status: z.literal("blocked"),
  blocker_code: z.string().min(1),
  blocker_owner: z.string().min(1),
  evidence_ids: z.array(z.string()).default([]),
  safe_next_step: z.string().min(1)
});

export type ResearchPacketV2PreviewRecord = z.infer<typeof ResearchPacketV2PreviewRecordSchema>;
export type ResearchPacketV2ActionResponse =
  | z.infer<typeof ResearchPacketV2ActionReadySchema>
  | z.infer<typeof ResearchPacketV2ActionBlockedSchema>;
