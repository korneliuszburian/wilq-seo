import { z } from "zod";

export const SocialHistoryInventorySourceSchema = z.object({
  channel: z.enum(["linkedin", "facebook"]),
  connector_id: z.enum(["linkedin", "facebook"]),
  inventory_status: z.enum(["missing", "review_ready"]),
  connector_access_status: z.enum(["configured", "missing_credentials", "unavailable"]),
  required_evidence_id: z.string(),
  required_metadata_fields: z.array(z.string()),
  safe_collection_mode: z.literal("metadata_only"),
  raw_post_body_allowed: z.literal(false)
});

export const SocialHistoryDiscoverySeedSchema = z.object({
  id: z.string(),
  channel: z.enum(["linkedin", "facebook"]),
  source_type: z.literal("public_posts_url"),
  source_url: z.string(),
  status: z.literal("seeded_not_collected"),
  safe_collection_mode: z.literal("metadata_only"),
  raw_post_body_allowed: z.literal(false),
  required_review: z.literal(true),
  operator_note: z.string()
});

export const SocialHistoryInventorySchema = z.object({
  contract: z.literal("social_history_inventory_v1"),
  read_only: z.literal(true),
  status: z.enum(["missing", "invalid", "review_ready"]),
  status_label: z.string(),
  duplicate_risk_status: z.literal("blocked_until_social_history_review"),
  required_sources: z.array(z.enum(["linkedin", "facebook"])),
  missing_evidence_ids: z.array(z.string()),
  metadata_source_configured: z.boolean(),
  metadata_source_status: z.enum(["not_configured", "invalid", "review_ready"]),
  item_count: z.number(),
  channel_counts: z.record(z.string(), z.number()),
  import_errors: z.array(z.string()),
  source_evidence_ids: z.array(z.string()).default([]),
  sources: z.array(SocialHistoryInventorySourceSchema),
  discovery_seeds: z.array(SocialHistoryDiscoverySeedSchema),
  input_template: z.object({
    contract: z.literal("social_history_inventory_v1"),
    collected_at: z.string(),
    reviewer: z.string(),
    items: z.array(z.object({
      channel: z.enum(["linkedin", "facebook"]),
      published_at: z.string(),
      topic: z.string(),
      service: z.string(),
      claim: z.string(),
      cta: z.string(),
      format: z.string(),
      post_url_or_id: z.string(),
      source_evidence_id: z.string()
    })),
    _instruction: z.string()
  }),
  allowed_uses: z.array(z.string()),
  blocked_uses: z.array(z.string()),
  dedupe_requirements: z.array(z.string()),
  operator_next_step: z.string()
});

export const SocialHistoryImportAuditSchema = z.object({
  contract: z.literal("social_history_inventory_v1"),
  read_only: z.literal(true),
  status: z.enum(["invalid", "review_ready"]),
  item_count: z.number(),
  channel_counts: z.record(z.string(), z.number()),
  missing_required_sources: z.array(z.enum(["linkedin", "facebook"])),
  required_metadata_fields: z.array(z.string()),
  forbidden_metadata_fields: z.array(z.string()),
  errors: z.array(z.string()),
  source_evidence_ids: z.array(z.string()).default([]),
  duplicate_free_claim_allowed: z.literal(false),
  publish_allowed: z.literal(false),
  operator_next_step: z.string()
});

