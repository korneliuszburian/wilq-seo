import { z } from "zod";

export const KnowledgeTaxonomyTypeSchema = z.enum([
  "client_truth",
  "expert_operating",
  "platform_trap",
  "workspace_memory",
  "observed_outcome"
]);

export const KnowledgeTaxonomyEntrySchema = z.object({
  id: KnowledgeTaxonomyTypeSchema,
  label: z.string().default(""),
  definition: z.string(),
  owned_by: z.enum([
    "source_fact_compiler",
    "expert_rule_compiler",
    "platform_rule_pack",
    "workspace_dossier",
    "measurement_loop"
  ]),
  allowed_usage: z.array(z.string()).default([]),
  forbidden_usage: z.array(z.string()).default([]),
  example_records: z.array(z.string()).default([])
}).superRefine((entry, ctx) => {
  const expectedOwnerByType: Record<z.infer<typeof KnowledgeTaxonomyTypeSchema>, string> = {
    client_truth: "source_fact_compiler",
    expert_operating: "expert_rule_compiler",
    platform_trap: "platform_rule_pack",
    workspace_memory: "workspace_dossier",
    observed_outcome: "measurement_loop"
  };
  if (entry.owned_by !== expectedOwnerByType[entry.id]) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["owned_by"],
      message: `Knowledge taxonomy type ${entry.id} must be owned by ${expectedOwnerByType[entry.id]}`
    });
  }
});

export const ExpertKnowledgeSourceSchema = z.object({
  id: z.string(),
  domain: z.string(),
  knowledge_type: KnowledgeTaxonomyTypeSchema,
  source_type: z.enum([
    "official_platform_doc",
    "repo_structured_rule",
    "reviewed_internal_sop",
    "public_site",
    "measurement_evidence",
    "workspace_memory"
  ]),
  license_status: z.enum([
    "commit_safe",
    "review_required",
    "private_reference_only"
  ]),
  source_reference: z.string(),
  freshness_date: z.string(),
  reviewer: z.string().nullable().optional(),
  trust_level: z.enum(["low", "medium", "high"]).default("medium"),
  allowed_usage: z.array(z.string()).min(1),
  forbidden_usage: z.array(z.string()).min(1),
  linked_rule_ids: z.array(z.string()).min(1)
});

export const KnowledgeCardSchema = z.object({
  id: z.string(),
  card_type: z.string(),
  card_type_label: z.string().default(""),
  title: z.string(),
  display_title: z.string().default(""),
  summary: z.string(),
  source_type: z.string(),
  source_type_label: z.string().default(""),
  source_id: z.string(),
  source_url_or_path: z.string(),
  extracted_at: z.string(),
  confidence: z.number(),
  last_seen_at: z.string(),
  source_lineage: z.array(z.string()),
  source_lineage_summary_label: z.string().default("")
});

export const MarketingPlaybookSchema = z.object({
  id: z.string(),
  family: z.string(),
  title: z.string(),
  display_title: z.string().default(""),
  card_type: z.string(),
  card_type_label: z.string().default(""),
  source_type_label: z.string().default(""),
  source_anchors: z.array(z.string()).min(1),
  required_evidence: z.array(z.string()).min(1),
  maps_to_opportunity_types: z.array(z.string()).min(1),
  maps_to_action_types: z.array(z.string()).min(1),
  expert_rule_ids: z.array(z.string()),
  compact_playbook: z.string(),
  refusal_rules: z.array(z.string()),
  output_contract: z.string(),
  source_path: z.string(),
  required_evidence_summary_label: z.string().default(""),
  mapped_action_type_summary_label: z.string().default("")
});

export const KnowledgeCompilerResultSchema = z.object({
  status: z.enum(["completed", "failed"]),
  generated_at: z.string(),
  card_count: z.number(),
  cards: z.array(KnowledgeCardSchema)
});

export const KnowledgeDecisionBindingSchema = z.object({
  id: z.string(),
  title: z.string(),
  status: z.enum(["ready", "blocked", "planned"]),
  status_label: z.string().default(""),
  route: z.string(),
  route_label: z.string().default(""),
  skill_id: z.string().nullable().optional(),
  summary: z.string(),
  next_step: z.string(),
  source_connectors: z.array(z.string()),
  source_connector_labels: z.array(z.string()).default([]),
  source_connector_summary_label: z.string().default(""),
  evidence_ids: z.array(z.string()),
  evidence_summary_label: z.string().default(""),
  action_ids: z.array(z.string()),
  action_summary_label: z.string().default(""),
  metric_tiles: z.record(z.string(), z.union([z.string(), z.number()])),
  knowledge_card_ids: z.array(z.string()),
  playbook_ids: z.array(z.string()),
  expert_rule_ids: z.array(z.string()),
  knowledge_summary_label: z.string().default(""),
  required_evidence: z.array(z.string()),
  required_evidence_summary_label: z.string().default(""),
  missing_contracts: z.array(z.string()),
  missing_contract_labels: z.array(z.string()).default([]),
  missing_contract_summary_label: z.string().default(""),
  missing_contract_detail_label: z.string().default(""),
  has_missing_contracts: z.boolean().default(false),
  blocked_claims: z.array(z.string()),
  blocked_claim_labels: z.array(z.string()).default([]),
  blocked_claim_summary_label: z.string().default(""),
  blocked_claim_count_summary_label: z.string().default(""),
  has_blocked_claims: z.boolean().default(false),
  source_lineage: z.array(z.string()),
  source_lineage_summary_label: z.string().default(""),
  risk: z.enum(["low", "medium", "high"]),
  risk_label: z.string().default("")
});

export const KnowledgeOperatingMapResponseSchema = z.object({
  generated_at: z.string(),
  source_card_count: z.number(),
  playbook_count: z.number(),
  expert_rule_count: z.number(),
  binding_count: z.number(),
  blocked_binding_summary_label: z.string().default(""),
  missing_contract_summary_label: z.string().default(""),
  blocked_claim_count_summary_label: z.string().default(""),
  bindings: z.array(KnowledgeDecisionBindingSchema)
});


