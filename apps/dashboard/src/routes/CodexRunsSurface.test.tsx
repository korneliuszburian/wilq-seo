import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CodexRunsSurface } from "./CodexRunsSurface";

const fixtures = vi.hoisted(() => {
  const detail = {
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
  };
  const summaries = [
    {
      id: detail.id,
      skill: detail.skill,
      status: detail.status,
      model: detail.model,
      prompt_template_id: detail.prompt_template_id,
      cost_estimate_pln: detail.cost_estimate_pln,
      source_material_count: 2,
      started_at: detail.started_at
    },
    {
      id: "codex_regulatory_source_fact_beta",
      skill: "wilq-content-operator",
      status: "blocked" as const,
      model: null,
      prompt_template_id: "regulatory_fact_proposal@v1",
      cost_estimate_pln: null,
      source_material_count: 0,
      started_at: "2026-08-08T09:00:00Z"
    }
  ];
  return {
    detail,
    summaries,
    historyPage: { items: summaries, total_count: 3, next_cursor: "opaque-page-2" },
    getCodexRunHistory: vi.fn(),
    getCodexRun: vi.fn()
  };
});

vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return {
    ...actual,
    getCodexRunHistory: fixtures.getCodexRunHistory,
    getCodexRun: fixtures.getCodexRun
  };
});

describe("CodexRunsSurface", () => {
  beforeEach(() => {
    fixtures.getCodexRunHistory.mockReset().mockResolvedValue(fixtures.historyPage);
    fixtures.getCodexRun.mockReset().mockResolvedValue(fixtures.detail);
  });

  afterEach(() => cleanup());

  it("renders server-page stats and fetches exact detail only after selection", async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={queryClient}>
        <CodexRunsSurface />
      </QueryClientProvider>
    );

    expect(await screen.findByRole("heading", { name: "Uruchomienia AI" })).toBeInTheDocument();
    expect(fixtures.getCodexRunHistory).toHaveBeenCalledWith(50, null);
    expect(fixtures.getCodexRun).not.toHaveBeenCalled();
    expect(screen.getByText(/Statystyki dotyczą bieżącej strony: 2 z 3/)).toBeInTheDocument();
    expect(
      screen.getByText(/Metadane promptu i pełny ślad uruchomienia są dostępne po wybraniu rekordu/)
    ).toBeInTheDocument();
    expect(screen.queryByText(/Surowe prompty są dostępne/)).not.toBeInTheDocument();
    const table = screen.getByRole("table");
    expect(within(table).getByText(/1,2345/)).toBeInTheDocument();
    expect(within(table).getByText("2")).toBeInTheDocument();

    fireEvent.click(
      within(table).getByRole("button", { name: /Pokaż szczegóły uruchomienia codex_cont/i })
    );

    expect(await screen.findByText("ev_content")).toBeInTheDocument();
    expect(fixtures.getCodexRun).toHaveBeenCalledWith("codex_content_initial_draft_alpha");
    expect(fixtures.getCodexRun).toHaveBeenCalledTimes(1);
    expect(screen.queryByText(/raw prompt/i)).not.toBeInTheDocument();
  });

  it("clears loaded detail before advancing with the opaque server cursor", async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const secondPage = {
      items: [fixtures.summaries[1]],
      total_count: 3,
      next_cursor: null
    };
    const secondDetail = { ...fixtures.detail, id: fixtures.summaries[1].id, evidence_ids: ["ev_regulatory"] };
    fixtures.getCodexRunHistory.mockImplementation((_limit, requestedCursor) =>
      Promise.resolve(requestedCursor === null ? fixtures.historyPage : secondPage)
    );
    fixtures.getCodexRun.mockImplementation((runId) =>
      Promise.resolve(runId === fixtures.summaries[1].id ? secondDetail : fixtures.detail)
    );
    render(
      <QueryClientProvider client={queryClient}>
        <CodexRunsSurface />
      </QueryClientProvider>
    );

    expect(await screen.findByRole("heading", { name: "Uruchomienia AI" })).toBeInTheDocument();
    const table = screen.getByRole("table");
    fireEvent.click(
      within(table).getByRole("button", { name: /Pokaż szczegóły uruchomienia codex_cont/i })
    );
    expect(await screen.findByText("ev_content")).toBeInTheDocument();
    expect(fixtures.getCodexRun).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole("button", { name: "Następna strona" }));

    await waitFor(() => expect(fixtures.getCodexRunHistory).toHaveBeenCalledWith(50, "opaque-page-2"));
    await waitFor(() => expect(screen.queryByText("ev_content")).not.toBeInTheDocument());
    expect(fixtures.getCodexRun).toHaveBeenCalledTimes(1);

    fireEvent.click(
      within(screen.getByRole("table")).getByRole("button", {
        name: /Pokaż szczegóły uruchomienia codex_regu/i
      })
    );
    expect(await screen.findByText("ev_regulatory")).toBeInTheDocument();
    expect(fixtures.getCodexRun).toHaveBeenCalledWith(fixtures.summaries[1].id);
    expect(fixtures.getCodexRun).toHaveBeenCalledTimes(2);
    expect(readFileSync("src/lib/api/codex.ts", "utf8")).not.toContain("/api/codex/runs\"");
  });

  it("owns the generated route instead of falling back to GenericSurface", () => {
    const appSource = readFileSync("src/routes/App.tsx", "utf8");

    expect(appSource).toContain('import("./CodexRunsSurface")');
    expect(appSource).toContain('"/codex-runs": () =>');
  });
});
