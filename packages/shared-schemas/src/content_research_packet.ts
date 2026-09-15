import { z } from "zod";

const Hex64Schema = z.string().regex(/^[0-9a-f]{64}$/);
const NonBlankStringSchema = z.string().trim().min(1);
const DateTimeSchema = z.string().datetime({ offset: true });

const ContentResearchPacketFreshnessSchema = z.strictObject({
  source_id: NonBlankStringSchema,
  evidence_ids: z.array(NonBlankStringSchema).default([]),
  checked_at: DateTimeSchema,
  status: z.enum(["fresh", "stale", "unknown"])
});

const ContentResearchPacketInternalLinkSchema = z.strictObject({
  destination_path: NonBlankStringSchema,
  anchor_text: NonBlankStringSchema,
  relation: z.enum(["supporting", "next_step", "source"]),
  verification: z.enum(["exact_verified", "planned", "blocked"])
});

const ContentResearchPacketBlockerSchema = z.strictObject({
  seam: z.enum([
    "preparation_receipt",
    "source_pack_binding",
    "identity_binding",
    "work_item_identity",
    "content_kind",
    "source_facts",
    "evidence",
    "freshness",
    "intent",
    "audience",
    "canonical_owner",
    "cta",
    "internal_links",
    "legal_requirements"
  ]),
  reason: z.enum([
    "preparation_receipt_missing",
    "preparation_receipt_mismatch",
    "preparation_receipt_conflict",
    "source_pack_binding_missing",
    "source_pack_binding_digest_mismatch",
    "source_pack_identity_mismatch",
    "source_pack_binding_blocked",
    "identity_binding_missing",
    "identity_binding_digest_mismatch",
    "identity_binding_blocked",
    "context_receipt_missing",
    "context_receipt_mismatch",
    "packet_conflict",
    "work_item_mismatch",
    "disposition_not_keep",
    "content_kind_ambiguous",
    "intent_missing",
    "query_cluster_missing",
    "audience_missing",
    "buyer_problem_missing",
    "buyer_trigger_missing",
    "canonical_owner_missing",
    "source_facts_missing",
    "source_fact_not_bound",
    "source_fact_not_registered",
    "source_fact_not_approved",
    "source_fact_registry_stale",
    "evidence_missing",
    "evidence_not_bound",
    "freshness_missing",
    "freshness_stale",
    "legal_requirements_missing",
    "cta_destination_missing",
    "cta_destination_invalid",
    "internal_links_missing",
    "internal_link_not_verified"
  ]),
  evidence_ids: z.array(NonBlankStringSchema).default([]),
  next_step_pl: NonBlankStringSchema
});

const ContentResearchPacketContextReceiptSchema = z.strictObject({
  schema_version: z.literal("wilq_content_research_packet_context_v1"),
  classification_run_id: NonBlankStringSchema,
  classification_run_digest: Hex64Schema,
  classification_source_row_digest: Hex64Schema,
  identity_binding_id: NonBlankStringSchema,
  identity_binding_digest: Hex64Schema,
  source_fact_authority_receipt_id: NonBlankStringSchema.nullable().optional(),
  source_fact_authority_receipt_digest: Hex64Schema.nullable().optional(),
  source_fact_authority_snapshot_digest: Hex64Schema.nullable().optional(),
  source_fact_authority_provenance_digest: Hex64Schema.nullable().optional(),
  service_card_id: NonBlankStringSchema.nullable().optional(),
  service_semantic_digest: Hex64Schema,
  brief_semantic_digest: Hex64Schema,
  demand_evidence_digest: Hex64Schema,
  verified_links_digest: Hex64Schema,
  regulatory_coverage_digest: Hex64Schema,
  freshness_digest: Hex64Schema,
  cta_destination: z.string().default(""),
  evidence_ids: z.array(NonBlankStringSchema).default([]),
  source_pack_evidence_ids: z.array(NonBlankStringSchema).default([]),
  source_fact_evidence_ids: z.array(NonBlankStringSchema).default([]),
  demand_evidence_ids: z.array(NonBlankStringSchema).default([]),
  measurement_evidence_ids: z.array(NonBlankStringSchema).default([]),
  verified_link_evidence_ids: z.array(NonBlankStringSchema).default([]),
  cta_evidence_ids: z.array(NonBlankStringSchema).default([]),
  regulatory_evidence_ids: z.array(NonBlankStringSchema).default([]),
  planning_evidence_ids: z.array(NonBlankStringSchema).default([])
});

export const ContentResearchPacketSchema = z.strictObject({
  schema_version: z.literal("wilq_content_research_packet_v1"),
  packet_id: NonBlankStringSchema,
  packet_digest: Hex64Schema,
  status: z.enum(["exact_current", "blocked"]),
  source_pack_binding_id: NonBlankStringSchema,
  source_pack_binding_digest: Hex64Schema,
  identity_binding_id: NonBlankStringSchema,
  identity_binding_digest: Hex64Schema,
  current_work_item_id: NonBlankStringSchema,
  preparation_receipt_id: NonBlankStringSchema.nullable().default(null),
  preparation_receipt_digest: Hex64Schema.nullable().default(null),
  classification_source_row_digest: z.string().default(""),
  canonical_path: z.string().default(""),
  public_url: z.string().default(""),
  final_disposition: z.enum(["keep", "noindex", "redirect", "remove"]).default("keep"),
  content_kind: z.enum(["service", "editorial", "landing_or_hub", "taxonomy_or_system", "ambiguous"]),
  intent: z.string().default(""),
  query_cluster: z.array(z.string()).default([]),
  canonical_owner: z.string().default(""),
  target_audience: z.string().default(""),
  buyer_problem: z.string().default(""),
  buyer_trigger: z.string().default(""),
  approved_source_fact_ids: z.array(NonBlankStringSchema).default([]),
  blocked_claims: z.array(NonBlankStringSchema).default([]),
  evidence_ids: z.array(NonBlankStringSchema).default([]),
  source_fact_registry_digest: z.string().default(""),
  source_facts_digest: Hex64Schema,
  evidence_ids_digest: Hex64Schema,
  freshness: z.array(ContentResearchPacketFreshnessSchema).default([]),
  legal_source_requirements: z.array(NonBlankStringSchema).default([]),
  cta_destination: z.string().default(""),
  internal_links: z.array(ContentResearchPacketInternalLinkSchema).default([]),
  context_receipt: ContentResearchPacketContextReceiptSchema.nullable().default(null),
  input_digest: Hex64Schema,
  blocker: ContentResearchPacketBlockerSchema.nullable().default(null),
  recorded_by: NonBlankStringSchema,
  recorded_at: DateTimeSchema
}).superRefine((packet, context) => {
  if ((packet.preparation_receipt_id == null) !== (packet.preparation_receipt_digest == null)) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["preparation_receipt_id"],
      message: "Preparation receipt ID and digest must be supplied together."
    });
  }
  if (packet.status === "exact_current" && (
    packet.preparation_receipt_id == null || packet.preparation_receipt_digest == null
  )) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["preparation_receipt_id"],
      message: "Exact research packets require a preparation receipt."
    });
  }
  if ((packet.status === "blocked") !== (packet.blocker !== null)) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["blocker"],
      message: "Blocked research packets require exactly one blocker."
    });
  }
  if (packet.status === "exact_current") {
    const requiredStrings = [
      "classification_source_row_digest",
      "canonical_path",
      "public_url",
      "canonical_owner",
      "intent",
      "target_audience",
      "buyer_problem",
      "buyer_trigger",
      "source_fact_registry_digest",
      "cta_destination"
    ] as const;
    for (const field of requiredStrings) {
      if (packet[field].trim().length === 0) {
        context.addIssue({
          code: z.ZodIssueCode.custom,
          path: [field],
          message: "Exact research packets require complete semantic fields."
        });
      }
    }
    if (packet.query_cluster.length === 0) {
      context.addIssue({ code: z.ZodIssueCode.custom, path: ["query_cluster"], message: "Exact packets require a query cluster." });
    }
    if (packet.approved_source_fact_ids.length === 0) {
      context.addIssue({ code: z.ZodIssueCode.custom, path: ["approved_source_fact_ids"], message: "Exact packets require approved source facts." });
    }
    if (packet.evidence_ids.length === 0) {
      context.addIssue({ code: z.ZodIssueCode.custom, path: ["evidence_ids"], message: "Exact packets require evidence IDs." });
    }
    if (packet.freshness.length === 0) {
      context.addIssue({ code: z.ZodIssueCode.custom, path: ["freshness"], message: "Exact packets require freshness receipts." });
    }
    if (packet.legal_source_requirements.length === 0) {
      context.addIssue({ code: z.ZodIssueCode.custom, path: ["legal_source_requirements"], message: "Exact packets require legal/source requirements." });
    }
    if (packet.internal_links.length === 0) {
      context.addIssue({ code: z.ZodIssueCode.custom, path: ["internal_links"], message: "Exact packets require verified internal links." });
    }
    if (packet.final_disposition !== "keep") {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["final_disposition"],
        message: "Only keep URLs may have an exact research packet."
      });
    }
  }
});

export const ContentResearchPacketCurrentProjectionSchema = z.strictObject({
  status: z.enum(["current", "blocked", "legacy"]),
  packet_id: NonBlankStringSchema,
  packet_digest: Hex64Schema,
  current_work_item_id: NonBlankStringSchema,
  current_source_pack_binding_id: NonBlankStringSchema.nullable(),
  current_source_pack_binding_digest: Hex64Schema.nullable(),
  current_identity_binding_id: NonBlankStringSchema.nullable(),
  current_identity_binding_digest: Hex64Schema.nullable(),
  blocker: ContentResearchPacketBlockerSchema.nullable(),
  revalidated_at: DateTimeSchema
}).superRefine((projection, context) => {
  if (projection.status === "current" && projection.blocker !== null) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["blocker"],
      message: "Current research packet projections cannot carry a blocker."
    });
  }
  if (projection.status !== "current" && projection.blocker === null) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["blocker"],
      message: "Blocked or legacy research packet projections require a blocker."
    });
  }
  if (projection.status === "current" && (
    projection.current_source_pack_binding_id === null
    || projection.current_source_pack_binding_digest === null
    || projection.current_identity_binding_id === null
    || projection.current_identity_binding_digest === null
  )) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["status"],
      message: "Current research packet projections require current packet identities."
    });
  }
});

export const ContentResearchPacketReadResultSchema = z.strictObject({
  status: z.literal("found"),
  packet: ContentResearchPacketSchema,
  current: ContentResearchPacketCurrentProjectionSchema
}).superRefine((result, context) => {
  if (
    result.packet.packet_id !== result.current.packet_id
    || result.packet.packet_digest !== result.current.packet_digest
    || result.packet.current_work_item_id !== result.current.current_work_item_id
  ) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["current"],
      message: "Packet and current projection identities must match exactly."
    });
  }
  if (result.packet.status === "blocked" && result.current.status === "current") {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["current", "status"],
      message: "A blocked packet cannot have a current projection."
    });
  }
});

/**
 * Verify the server-owned packet digest and derived ID in the browser without
 * a synchronous hashing fallback. The payload mirrors the server's canonical
 * digest and logical-ID scopes.
 */
export async function verifyContentResearchPacketDigest(value: unknown): Promise<boolean> {
  const parsed = ContentResearchPacketSchema.safeParse(value);
  if (!parsed.success || !globalThis.crypto?.subtle) return false;
  try {
    const sourceFactsDigest = await sha256Hex({
      values: parsed.data.approved_source_fact_ids
    });
    if (sourceFactsDigest !== parsed.data.source_facts_digest) return false;
    const evidenceIdsDigest = await sha256Hex({
      values: parsed.data.evidence_ids
    });
    if (evidenceIdsDigest !== parsed.data.evidence_ids_digest) return false;
    const inputDigest = await sha256Hex(researchPacketCommandPayload(parsed.data));
    if (inputDigest !== parsed.data.input_digest) return false;

    const payload: Record<string, unknown> = { ...parsed.data };
    delete payload.packet_id;
    delete payload.packet_digest;
    delete payload.recorded_by;
    delete payload.recorded_at;
    const observedDigest = await sha256Hex(payload);
    const logicalId = await sha256Hex({
      source_pack_binding_id: parsed.data.source_pack_binding_id,
      source_pack_binding_digest: parsed.data.source_pack_binding_digest,
      identity_binding_id: parsed.data.identity_binding_id,
      identity_binding_digest: parsed.data.identity_binding_digest,
      current_work_item_id: parsed.data.current_work_item_id,
      input_digest: parsed.data.input_digest
    });
    return (
      observedDigest === parsed.data.packet_digest &&
      parsed.data.packet_id === `content_research_packet_${logicalId.slice(0, 24)}`
    );
  } catch {
    return false;
  }
}

function researchPacketCommandPayload(
  packet: z.infer<typeof ContentResearchPacketSchema>
): Record<string, unknown> {
  return {
    source_pack_binding_id: packet.source_pack_binding_id,
    source_pack_binding_digest: packet.source_pack_binding_digest,
    identity_binding_id: packet.identity_binding_id,
    identity_binding_digest: packet.identity_binding_digest,
    current_work_item_id: packet.current_work_item_id,
    content_kind: packet.content_kind,
    intent: packet.intent,
    query_cluster: packet.query_cluster,
    canonical_owner: packet.canonical_owner,
    target_audience: packet.target_audience,
    buyer_problem: packet.buyer_problem,
    buyer_trigger: packet.buyer_trigger,
    approved_source_fact_ids: packet.approved_source_fact_ids,
    blocked_claims: packet.blocked_claims,
    evidence_ids: packet.evidence_ids,
    freshness: packet.freshness,
    legal_source_requirements: packet.legal_source_requirements,
    cta_destination: packet.cta_destination,
    internal_links: packet.internal_links,
    context_receipt: packet.context_receipt
  };
}

export const verifyContentResearchPacketIntegrity = verifyContentResearchPacketDigest;

async function sha256Hex(value: unknown): Promise<string> {
  const bytes = new TextEncoder().encode(canonicalJson(value));
  const hash = await globalThis.crypto.subtle.digest("SHA-256", bytes);
  return Array.from(
    new Uint8Array(hash),
    (byte) => byte.toString(16).padStart(2, "0")
  ).join("");
}

function canonicalJson(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
  if (value !== null && typeof value === "object") {
    const object = value as Record<string, unknown>;
    return `{${Object.keys(object)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${canonicalJson(object[key])}`)
      .join(",")}}`;
  }
  if (typeof value === "number" && !Number.isFinite(value)) {
    throw new TypeError("Canonical JSON cannot contain non-finite numbers.");
  }
  const serialized = JSON.stringify(value);
  if (serialized === undefined) throw new TypeError("Canonical JSON cannot contain undefined.");
  return serialized;
}

export type ContentResearchPacket = z.infer<typeof ContentResearchPacketSchema>;
export type ContentResearchPacketCurrentProjection = z.infer<
  typeof ContentResearchPacketCurrentProjectionSchema
>;
export type ContentResearchPacketReadResult = z.infer<
  typeof ContentResearchPacketReadResultSchema
>;
