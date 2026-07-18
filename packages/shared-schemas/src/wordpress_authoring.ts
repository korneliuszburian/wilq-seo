import { z } from "zod";

import {
  ContentDraftPackageSchema,
  ContentWordPressDraftHandoffSchema
} from "./contentWorkflow";

const WordPressAuthoringReadinessSchema = z.enum([
  "available",
  "configured",
  "not_configured",
  "missing",
  "blocked",
  "unknown"
]);

const WordPressAuthoringDiscoveryMethodSchema = z.enum([
  "rest",
  "acf_rest",
  "acf_export",
  "wp_cli",
  "helper",
  "env_config"
]);

const WordPressAuthoringBlockerSchema = z.object({
  code: z.string(),
  label: z.string(),
  reason: z.string(),
  next_step: z.string(),
  source_ref: z.string().nullable().optional()
});

const WordPressAuthoringDevSectionSchema = z.object({
  section_index: z.number(),
  acf_field_name: z.string(),
  layout_name: z.string(),
  layout_label: z.string(),
  title: z.string().default(""),
  text_summary: z.string().default(""),
  field_names: z.array(z.string()).default([]),
  text_field_paths: z.array(z.string()).default([])
});

const WordPressAuthoringDevPageSchema = z.object({
  post_id: z.string(),
  slug: z.string(),
  title: z.string(),
  link: z.string(),
  status: z.string(),
  modified: z.string(),
  modified_gmt: z.string(),
  template: z.string().default(""),
  parent: z.string().default(""),
  acf_field_name: z.string().nullable().optional(),
  section_count: z.number().default(0),
  sections: z.array(WordPressAuthoringDevSectionSchema).default([])
});

export const WordPressAuthoringProfileSchema = z.object({
  profile_version: z.literal("wordpress_authoring_profile_v1"),
  connector: z.string(),
  site_kind: z.string(),
  authoring_target: z.string(),
  discovery_mode: z.string(),
  discovery_order: z.array(WordPressAuthoringDiscoveryMethodSchema),
  rest_api: z.object({
    method: z.literal("rest"),
    status: WordPressAuthoringReadinessSchema,
    base_url_configured: z.boolean(),
    auth_configured: z.boolean(),
    public_url_configured: z.boolean(),
    post_types: z.array(z.string())
  }),
  acf: z.object({
    enabled_state: z.enum(["enabled", "disabled", "unknown"]),
    rest_enabled_state: z.enum(["enabled", "disabled", "unknown"]),
    flexible_content_field_name: z.string().nullable().optional(),
    post_types: z.array(z.string()),
    layouts: z.array(
      z.object({
        name: z.string(),
        label: z.string(),
        fields: z.array(z.record(z.string(), z.unknown())),
        source_method: WordPressAuthoringDiscoveryMethodSchema,
        required_field_names: z.array(z.string()),
        optional_field_names: z.array(z.string())
      })
    ),
    source_method: WordPressAuthoringDiscoveryMethodSchema.nullable().optional(),
    layouts_discovered: z.boolean()
  }),
  dev_content: z.object({
    status: WordPressAuthoringReadinessSchema,
    source_method: WordPressAuthoringDiscoveryMethodSchema.nullable().optional(),
    source_ref: z.string(),
    page_count: z.number(),
    pages: z.array(WordPressAuthoringDevPageSchema).default([]),
    blockers: z.array(WordPressAuthoringBlockerSchema).default([])
  }),
  wp_cli: z.object({
    method: z.literal("wp_cli"),
    status: WordPressAuthoringReadinessSchema,
    configured: z.boolean(),
    missing_env: z.array(z.string()),
    source_refs: z.array(z.string())
  }),
  helper_plugin: z.object({
    method: z.literal("helper"),
    status: WordPressAuthoringReadinessSchema,
    configured: z.boolean(),
    missing_env: z.array(z.string()),
    source_refs: z.array(z.string())
  }),
  write_boundary: z.object({
    allowed_operation: z.literal("create_wordpress_draft"),
    direct_vendor_write_allowed: z.literal(false),
    draft_writes_enabled_by_env: z.boolean(),
    live_write_enabled: z.literal(false),
    publish_allowed: z.literal(false),
    destructive_update_allowed: z.literal(false),
    external_write_attempted: z.literal(false),
    required_action_contract: z.literal("actionobject_validate_preview_review_confirm_audit")
  }),
  discovery_facts: z.array(z.record(z.string(), z.unknown())),
  blockers: z.array(WordPressAuthoringBlockerSchema),
  evidence_ids: z.array(z.string()),
  source_connectors: z.array(z.string())
});

const ContentWordPressAuthoringPayloadPreviewBlockerSchema = z.object({
  code: z.string(),
  label: z.string(),
  reason: z.string(),
  next_step: z.string()
});

type ContentWordPressFieldValuePreviewShape = {
  field_name: string;
  field_label: string;
  field_type: string;
  value_preview?: string | null;
  safe_to_autofill: boolean;
  note?: string | null;
  nested_values: ContentWordPressFieldValuePreviewShape[];
  row_candidates: ContentWordPressFieldRowCandidateShape[];
};

type ContentWordPressRowCandidateFieldShape = {
  field_name: string;
  field_label: string;
  field_type: string;
  value_preview?: string | null;
  safe_to_autofill: boolean;
  note?: string | null;
};

type ContentWordPressFieldRowCandidateShape = {
  row_type: "acf_repeater_row" | "acf_flexible_content_row";
  row_label: string;
  review_status: "review_required";
  note: string;
  field_values: ContentWordPressRowCandidateFieldShape[];
  evidence_ids: string[];
};

const ContentWordPressRowCandidateFieldSchema = z.object({
  field_name: z.string(),
  field_label: z.string(),
  field_type: z.string(),
  value_preview: z.string().nullable().optional(),
  safe_to_autofill: z.boolean(),
  note: z.string().nullable().optional()
});

const ContentWordPressFieldRowCandidateSchema = z.object({
  row_type: z.enum(["acf_repeater_row", "acf_flexible_content_row"]),
  row_label: z.string(),
  review_status: z.literal("review_required"),
  note: z.string(),
  field_values: z.array(ContentWordPressRowCandidateFieldSchema).default([]),
  evidence_ids: z.array(z.string()).default([])
});

const ContentWordPressFieldValuePreviewSchema: z.ZodType<
  ContentWordPressFieldValuePreviewShape
> = z.lazy(() =>
  z.object({
    field_name: z.string(),
    field_label: z.string(),
    field_type: z.string(),
    value_preview: z.string().nullable().optional(),
    safe_to_autofill: z.boolean(),
    note: z.string().nullable().optional(),
    nested_values: z.array(ContentWordPressFieldValuePreviewSchema).default([]),
    row_candidates: z.array(ContentWordPressFieldRowCandidateSchema).default([])
  })
);

const ContentWordPressFlexibleSectionPayloadSchema = z.object({
  layout_name: z.string(),
  layout_label: z.string(),
  section_heading: z.string(),
  field_values: z.record(z.string(), z.string().nullable()),
  field_previews: z.array(ContentWordPressFieldValuePreviewSchema).default([]),
  missing_required_fields: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()).default([])
});

export const ContentWordPressAuthoringPayloadPreviewResultSchema = z.object({
  status: z.enum(["ready", "blocked"]),
  mode: z.literal("dry_run"),
  connector: z.literal("wordpress_ekologus"),
  endpoint_kind: z.literal("posts"),
  post_status: z.literal("draft"),
  flexible_content_field_name: z.string().nullable().optional(),
  sections: z.array(ContentWordPressFlexibleSectionPayloadSchema).default([]),
  publish_allowed: z.literal(false),
  destructive_update_allowed: z.literal(false),
  external_write_attempted: z.literal(false),
  required_action_contract: z.literal("actionobject_validate_preview_review_confirm_audit"),
  blockers: z.array(ContentWordPressAuthoringPayloadPreviewBlockerSchema).default([])
});

export const ContentWorkItemWordPressAuthoringPayloadPreviewRequestSchema = z.object({
  handoff: ContentWordPressDraftHandoffSchema.nullable().optional(),
  draft_package: ContentDraftPackageSchema.nullable().optional(),
  authoring_profile: WordPressAuthoringProfileSchema.nullable().optional()
});

export const ContentWorkItemWordPressAuthoringPayloadPreviewResponseSchema = z.object({
  authoring_profile: WordPressAuthoringProfileSchema,
  preview_result: ContentWordPressAuthoringPayloadPreviewResultSchema
});


