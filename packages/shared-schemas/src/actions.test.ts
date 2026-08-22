import { describe, expect, it } from "vitest";

import { CodexRunHistoryPageSchema, CodexRunSchema } from "./actions";

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

describe("CodexRunHistoryPageSchema", () => {
  it("accepts lightweight summaries and rejects full trace fields", () => {
    const page = CodexRunHistoryPageSchema.parse({
      items: [
        {
          id: "codex_summary",
          skill: "wilq-content-operator",
          status: "completed",
          model: "gpt-5.6-sol",
          prompt_template_id: "content_initial_draft@v2",
          cost_estimate_pln: 1.25,
          source_material_count: 2,
          started_at: "2026-08-22T10:00:00Z"
        }
      ],
      total_count: 3,
      next_cursor: "opaque"
    });

    expect(page.items[0]?.source_material_count).toBe(2);
    expect(
      CodexRunHistoryPageSchema.safeParse({
        ...page,
        items: [{ ...page.items[0], prompt_digest: "a".repeat(64) }]
      }).success
    ).toBe(false);
  });
});
