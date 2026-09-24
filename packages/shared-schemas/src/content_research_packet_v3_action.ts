import { z } from "zod";

import { ActionObjectSchema } from "./actions";

const Hex64Schema = z.string().regex(/^[0-9a-f]{64}$/);
const NonBlankStringSchema = z.string().min(1);
const SAFE_PUBLIC_HOSTS = new Set([
  "www.ekologus.pl",
  "ekologus.pl",
  "sklep.ekologus.pl"
]);
const UNSAFE_URL_CHARACTER = /[\x00-\x20\x7f<>"'`()\[\]{}|\\^]/;

export function isSafeResearchPacketV3PageUrl(value: string): boolean {
  if (!value || value !== value.trim() || UNSAFE_URL_CHARACTER.test(value)) return false;
  const match = /^https:\/\/([^/]+)(\/[\s\S]*)$/i.exec(value);
  const authority = match?.[1];
  if (!authority) return false;
  try {
    const url = new URL(value);
    return (
      url.protocol === "https:"
      && SAFE_PUBLIC_HOSTS.has(url.hostname)
      && authority.toLowerCase() === url.hostname
      && !url.username
      && !url.password
      && !url.port
      && !url.search
      && !url.hash
    );
  } catch {
    return false;
  }
}

export function isSafeResearchPacketV3OfficialSourceUrl(value: string): boolean {
  if (!value || value !== value.trim() || UNSAFE_URL_CHARACTER.test(value)) return false;
  try {
    const url = new URL(value);
    return (
      url.protocol === "https:"
      && Boolean(url.hostname)
      && !url.username
      && !url.password
    );
  } catch {
    return false;
  }
}

const CanonicalPathSchema = NonBlankStringSchema.refine(
  (value) => (
    value === value.trim()
    && value.startsWith("/")
    && !/[\x00-\x20\x7f?#]/.test(value)
  ),
  "Canonical path must be an exact path."
);

export const ResearchPacketV3FactSchema = z.object({
  source_fact_id: NonBlankStringSchema,
  fact_digest: Hex64Schema,
  text: NonBlankStringSchema,
  source_reference: NonBlankStringSchema,
  freshness_date: NonBlankStringSchema,
  source_type: z.literal("legal_update"),
  official_source: z.literal(true),
  privacy_class: z.literal("commit_safe"),
  source_connectors: z.array(z.literal("official_regulatory_review")).min(1),
  evidence_ids: z.array(NonBlankStringSchema).min(1),
  regulatory_requirement_ids: z.array(NonBlankStringSchema).min(1)
}).strict();

export const ResearchPacketV3PlanningContextSchema = z.object({
  target_reader: NonBlankStringSchema,
  buyer_problem: NonBlankStringSchema,
  buyer_trigger: NonBlankStringSchema,
  search_intent: NonBlankStringSchema.nullable().optional()
}).strict();

export const ResearchPacketV3InternalLinkSchema = z.object({
  target_url: NonBlankStringSchema,
  anchor_hint: NonBlankStringSchema,
  source_connector: z.literal("wordpress_ekologus").default("wordpress_ekologus"),
  evidence_ids: z.array(NonBlankStringSchema).min(1)
}).strict();

export const ResearchPacketV3LegalRequirementSchema = z.object({
  requirement_id: NonBlankStringSchema,
  label: NonBlankStringSchema,
  source_fact_ids: z.array(NonBlankStringSchema).min(1),
  evidence_ids: z.array(NonBlankStringSchema).min(1)
}).strict();

export const ResearchPacketV3BlockerSchema = z.object({
  code: NonBlankStringSchema,
  owner: NonBlankStringSchema,
  evidence_ids: z.array(NonBlankStringSchema).default([]),
  safe_next_step: NonBlankStringSchema
}).strict();

export const ResearchPacketV3PreviewReadySchema = z.object({
  contract_version: z.literal("research_packet_v3_preview"),
  status: z.literal("ready"),
  work_item_id: NonBlankStringSchema,
  preview_id: NonBlankStringSchema,
  preview_hash: Hex64Schema,
  source_pack_id: NonBlankStringSchema,
  source_pack_hash: Hex64Schema,
  // These are optional only for immutable v3 snapshots written before page identity.
  page_url: NonBlankStringSchema.nullable().optional(),
  canonical_path: CanonicalPathSchema.nullable().optional(),
  // Historical v3 previews predate explicit content-subject binding.
  content_kind: z.enum(["service", "editorial"]).optional(),
  service_card_id: NonBlankStringSchema.nullable().optional(),
  identity_digest: Hex64Schema,
  material_meaning_digest: Hex64Schema,
  planning_input_digest: Hex64Schema,
  demand_evidence_status: z.enum(["available", "missing"]),
  selected_facts: z.array(ResearchPacketV3FactSchema).min(1),
  planning_context: ResearchPacketV3PlanningContextSchema,
  cta_direction: NonBlankStringSchema,
  minimum_cta_blocks: z.number().int().min(1).max(4),
  required_cta_patterns: z.array(NonBlankStringSchema),
  internal_links: z.array(ResearchPacketV3InternalLinkSchema).min(1),
  regulatory_profile_id: NonBlankStringSchema,
  regulatory_profile_version: NonBlankStringSchema,
  legal_requirements: z.array(ResearchPacketV3LegalRequirementSchema).min(1),
  verification_evidence_ids: z.array(NonBlankStringSchema).min(1),
  verification_evidence_digest: Hex64Schema,
  blocker: z.null().optional(),
  generation_allowed: z.literal(false),
  packet_write_allowed: z.literal(false)
}).strict().superRefine((packet, context) => {
  if (packet.preview_id !== `content_research_packet_v3_${packet.preview_hash.slice(0, 24)}`) {
    context.addIssue({ code: "custom", message: "Research packet preview identity mismatch." });
  }
  if (packet.source_pack_id !== `source_pack_v3_${packet.source_pack_hash}`) {
    context.addIssue({ code: "custom", message: "Research packet source pack identity mismatch." });
  }
  if (packet.demand_evidence_status === "missing" && packet.planning_context.search_intent) {
    context.addIssue({ code: "custom", message: "Missing demand cannot carry search intent." });
  }
  if ((packet.page_url === undefined || packet.page_url === null)
    !== (packet.canonical_path === undefined || packet.canonical_path === null)) {
    context.addIssue({ code: "custom", message: "Research packet page identity is incomplete." });
  }
  if (packet.content_kind === "service" && !packet.service_card_id) {
    context.addIssue({ code: "custom", message: "Service packet subject requires a card ID." });
  }
  if (packet.content_kind === "editorial" && packet.service_card_id != null) {
    context.addIssue({ code: "custom", message: "Editorial packet cannot carry a service card ID." });
  }
  if (packet.content_kind === undefined && packet.service_card_id != null) {
    context.addIssue({ code: "custom", message: "Historical packet cannot carry an unversioned card ID." });
  }
});

export const ResearchPacketV3PreviewBlockedSchema = z.object({
  contract_version: z.literal("research_packet_v3_preview"),
  status: z.literal("blocked"),
  work_item_id: NonBlankStringSchema,
  blocker: ResearchPacketV3BlockerSchema,
  generation_allowed: z.literal(false),
  packet_write_allowed: z.literal(false)
});

export const ResearchPacketV3PreviewResponseSchema = z.discriminatedUnion("status", [
  ResearchPacketV3PreviewReadySchema,
  ResearchPacketV3PreviewBlockedSchema
]);

export const ResearchPacketV3PreviewRecordSchema = z.object({
  schema_version: z.literal("wilq_research_packet_v3_preview_record_v1"),
  preview_hash: Hex64Schema,
  work_item_id: NonBlankStringSchema,
  snapshot: ResearchPacketV3PreviewReadySchema
}).strict().superRefine((record, context) => {
  if (
    record.preview_hash !== record.snapshot.preview_hash
    || record.work_item_id !== record.snapshot.work_item_id
  ) {
    context.addIssue({ code: "custom", message: "Research packet record identity mismatch." });
  }
});

export type ResearchPacketV3PreviewRecord = z.infer<typeof ResearchPacketV3PreviewRecordSchema>;
type ResearchPacketV3ReviewableSnapshot = Omit<
  ResearchPacketV3PreviewRecord["snapshot"],
  "page_url" | "canonical_path"
> & {
  page_url: string;
  canonical_path: string;
};
export type ResearchPacketV3ReviewablePreviewRecord = Omit<
  ResearchPacketV3PreviewRecord,
  "snapshot"
> & { snapshot: ResearchPacketV3ReviewableSnapshot };

export function hasReviewableResearchPacketV3PageIdentity(
  record: ResearchPacketV3PreviewRecord
): record is ResearchPacketV3ReviewablePreviewRecord {
  const { page_url: pageUrl, canonical_path: canonicalPath } = record.snapshot;
  if (
    typeof pageUrl !== "string"
    || typeof canonicalPath !== "string"
    || !isSafeResearchPacketV3PageUrl(pageUrl)
    || !CanonicalPathSchema.safeParse(canonicalPath).success
  ) {
    return false;
  }
  const rawPathname = /^https:\/\/[^/]+(\/[\s\S]*)$/i.exec(pageUrl)?.[1];
  if (!rawPathname) return false;
  const normalizedPath = rawPathname.replace(/\/+$/, "") || "/";
  return normalizedPath === canonicalPath;
}

export const ResearchPacketV3ReviewablePreviewRecordSchema = ResearchPacketV3PreviewRecordSchema
  .refine(hasReviewableResearchPacketV3PageIdentity, {
    message: "Research packet needs an exact safe page URL and canonical path for review."
  });

const ResearchPacketV3ActionResponseCommonSchema = z.object({
  response_type: z.literal("research_packet_v3_action"),
  external_write_attempted: z.literal(false),
  generation_allowed: z.literal(false)
});

export const ResearchPacketV3ActionReadySchema = ResearchPacketV3ActionResponseCommonSchema.extend({
  status: z.literal("preview_ready"),
  action_id: NonBlankStringSchema,
  action: ActionObjectSchema,
  preview: ResearchPacketV3PreviewReadySchema
});

export const ResearchPacketV3ActionBlockedSchema = ResearchPacketV3ActionResponseCommonSchema.extend({
  status: z.literal("blocked"),
  work_item_id: NonBlankStringSchema,
  blocker_code: NonBlankStringSchema,
  blocker_owner: NonBlankStringSchema,
  evidence_ids: z.array(NonBlankStringSchema).default([]),
  safe_next_step: NonBlankStringSchema
});

export const ResearchPacketV3ActionResponseSchema = z.discriminatedUnion("status", [
  ResearchPacketV3ActionReadySchema,
  ResearchPacketV3ActionBlockedSchema
]);

export type ResearchPacketV3PreviewResponse = z.infer<typeof ResearchPacketV3PreviewResponseSchema>;
export type ResearchPacketV3ActionResponse = z.infer<typeof ResearchPacketV3ActionResponseSchema>;
