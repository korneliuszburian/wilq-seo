import { z } from "zod";

import { ActionObjectSchema } from "./actions";
import { ConnectorStatusSchema, EvidenceSchema } from "./connectors";
import { SocialHistoryInventorySchema } from "./social_history";

export const SocialDraftContextSchema = z.object({
  mode: z.literal("review_only"),
  publish_allowed: z.literal(false),
  missing_publish_access: z.record(z.string(), z.array(z.string())),
  draft_action_ids: z.array(z.string()),
  source_inputs: z.array(z.record(z.string(), z.unknown())),
  draft_constraints: z.array(z.string()),
  blocked_claims: z.array(z.string()),
  source_metric_names: z.array(z.string()).optional(),
  source_connectors: z.array(z.string()).optional(),
  evidence_ids: z.array(z.string()).optional(),
  historical_social_inventory_status: z.enum(["missing", "invalid", "review_ready"]),
  historical_social_inventory_status_label: z.string(),
  duplicate_risk_status: z.literal("blocked_until_social_history_review"),
  duplicate_risk_status_label: z.string(),
  required_history_sources: z.array(z.enum(["linkedin", "facebook"])),
  missing_history_evidence: z.array(z.string()),
  social_history_inventory: SocialHistoryInventorySchema,
  history_audit_endpoint: z.literal("/api/social/history-inventory/audit"),
  history_audit_contract: z.literal("social_history_inventory_v1"),
  operator_next_step: z.string()
});

export const SocialPublisherContextPackSchema = z.object({
  strict_instruction: z.string(),
  connector_status: z.array(ConnectorStatusSchema),
  active_action_objects: z.array(ActionObjectSchema),
  evidence_summaries: z.array(EvidenceSchema),
  social_draft_context: SocialDraftContextSchema
});


