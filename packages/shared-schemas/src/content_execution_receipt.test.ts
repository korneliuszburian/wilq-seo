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
  expected_content_digest: "a".repeat(64),
  observed_content_digest: "b".repeat(64),
  expected_acf_digest: null,
  observed_acf_digest: null,
  expected_title_digest: "c".repeat(64),
  observed_title_digest: "d".repeat(64),
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

  it("preserves expected and observed digest fields", () => {
    const parsed = ContentWordPressDraftExecutionResultSchema.parse(executionReceipt);
    expect(parsed.observed_content_digest).toBe("b".repeat(64));
    expect(parsed.observed_title_digest).toBe("d".repeat(64));
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
