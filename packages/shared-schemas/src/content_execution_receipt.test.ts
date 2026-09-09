import { describe, expect, it } from "vitest";

import { ContentWordPressDraftExecutionResultSchema } from "./contentWorkflow";

const executionReceipt = {
  status: "created",
  mode: "live",
  boundary: {
    allowed_operation: "create_wordpress_draft",
    dry_run_default: true,
    live_write_enabled: true,
    live_adapter_configured: true,
    publish_allowed: false,
    destructive_update_allowed: false
  },
  wordpress_post_id: "417",
  external_write_attempted: true
};

describe("content draft execution receipt browser contract", () => {
  it("preserves a persisted pages endpoint", () => {
    expect(
      ContentWordPressDraftExecutionResultSchema.parse({
        ...executionReceipt,
        endpoint: "pages"
      }).endpoint
    ).toBe("pages");
  });

  it("rejects an unsupported persisted endpoint", () => {
    expect(
      ContentWordPressDraftExecutionResultSchema.safeParse({
        ...executionReceipt,
        endpoint: "news"
      }).success
    ).toBe(false);
  });
});
