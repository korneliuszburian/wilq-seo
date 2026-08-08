import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CodexRunsSurface } from "./CodexRunsSurface";

const runs = vi.hoisted(() => [
  {
    id: "codex_content_initial_draft_alpha",
    skill: "wilq-content-operator",
    hook: "content_initial_full_draft",
    source: "wilq_api",
    status: "completed" as const,
    model: "gpt-5.6-sol",
    model_reasoning_effort: "xhigh",
    prompt_digest: "a".repeat(64),
    prompt_template_id: "content_initial_draft@v1",
    token_usage_input: 1200,
    token_usage_output: 450,
    cost_estimate_pln: 1.2345,
    used_endpoints: ["/api/content/work-items/bdo/initial-draft"],
    evidence_ids: ["ev_content"],
    source_material_ids: ["source_material_bdo", "source_material_regulation"],
    action_ids: [],
    proposal_id: "content_planning_proposal_bdo",
    planning_digest: "b".repeat(64),
    planning_input_digest: "c".repeat(64),
    initial_draft_context_digest: "d".repeat(64),
    initial_draft_base_revision_id: null,
    started_at: "2026-08-08T10:00:00Z",
    deadline_at: null,
    completed_at: "2026-08-08T10:01:00Z",
    error: null
  },
  {
    id: "codex_regulatory_source_fact_beta",
    skill: "wilq-content-operator",
    hook: "content_regulatory_source_fact_proposal",
    source: "wilq_api",
    status: "blocked" as const,
    model: null,
    model_reasoning_effort: null,
    prompt_digest: null,
    prompt_template_id: "regulatory_fact_proposal@v1",
    token_usage_input: null,
    token_usage_output: null,
    cost_estimate_pln: null,
    used_endpoints: [],
    evidence_ids: ["ev_regulatory"],
    source_material_ids: [],
    action_ids: [],
    proposal_id: null,
    planning_digest: null,
    planning_input_digest: null,
    initial_draft_context_digest: null,
    initial_draft_base_revision_id: null,
    started_at: "2026-08-08T09:00:00Z",
    deadline_at: null,
    completed_at: "2026-08-08T09:01:00Z",
    error: "source_blocked"
  }
]);

vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return { ...actual, getCodexRuns: vi.fn().mockResolvedValue(runs) };
});

describe("CodexRunsSurface", () => {
  afterEach(() => cleanup());

  it("renders run cost and material count, then opens full trace details", async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={queryClient}>
        <CodexRunsSurface />
      </QueryClientProvider>
    );

    expect(await screen.findByRole("heading", { name: "Uruchomienia AI" })).toBeInTheDocument();
    const table = screen.getByRole("table");
    expect(within(table).getByText(/1,2345/)).toBeInTheDocument();
    expect(within(table).getByText("2")).toBeInTheDocument();
    expect(within(table).getByText("content_initial_draft@v1")).toBeInTheDocument();

    fireEvent.click(
      within(table).getByRole("button", { name: /Pokaż szczegóły uruchomienia codex_regu/i })
    );
    expect(screen.getByText("source_blocked")).toBeInTheDocument();
    expect(screen.getByText("ev_regulatory")).toBeInTheDocument();
    expect(screen.queryByText(/raw prompt/i)).not.toBeInTheDocument();
  });

  it("owns the generated route instead of falling back to GenericSurface", () => {
    const appSource = readFileSync("src/routes/App.tsx", "utf8");

    expect(appSource).toContain('import("./CodexRunsSurface")');
    expect(appSource).toContain('"/codex-runs": () =>');
  });
});
