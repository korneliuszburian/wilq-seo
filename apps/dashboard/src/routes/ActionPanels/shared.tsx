import {
  ContentDraftRevisionBindingSchema,
  type ContentDraftRevisionBinding
} from "@wilq/shared-schemas";

import type { ActionObject } from "../../lib/api";

export type { ActionObject };

export type ActionPanelProps = {
  action: ActionObject;
};

export type PayloadRecord = Record<string, unknown>;

export function contentDevDraftBinding(
  action: ActionObject
): ContentDraftRevisionBinding | undefined {
  if (action.payload.action_type !== "content_dev_draft_create") return undefined;
  const parsed = ContentDraftRevisionBindingSchema.safeParse(
    action.payload.wordpress_draft_binding
  );
  return parsed.success ? parsed.data : undefined;
}
