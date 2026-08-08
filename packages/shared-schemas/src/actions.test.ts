import { describe, expect, it } from "vitest";

import { CodexRunSchema } from "./actions";

describe("CodexRunSchema", () => {
  it("validates the AI trace and strips fields that could expose a raw prompt", () => {
    const parsed = CodexRunSchema.parse({
      id: "codex_trace_test",
      status: "completed",
      model: "gpt-5.6-sol",
      model_reasoning_effort: "xhigh",
      prompt_digest: "a".repeat(64),
      prompt_template_id: "content_initial_draft@v1",
      token_usage_input: 1200,
      token_usage_output: 450,
      cost_estimate_pln: 1.2345,
      source_material_ids: ["source_material_bdo"],
      started_at: "2026-08-08T10:00:00Z",
      prompt: "raw prompt must not cross this boundary"
    });

    expect(parsed.model).toBe("gpt-5.6-sol");
    expect(parsed.cost_estimate_pln).toBe(1.2345);
    expect(parsed.source_material_ids).toEqual(["source_material_bdo"]);
    expect(parsed).not.toHaveProperty("prompt");
  });
});
