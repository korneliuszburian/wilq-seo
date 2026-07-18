import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { getKnowledgeSourceMaterialReadiness } from "../lib/api";
import { ContentPlanningGenerationPanel } from "./ContentPlanningGenerationPanel";

vi.mock("../lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../lib/api")>()),
  getContentWorkItemPlanningProposal: vi.fn().mockResolvedValue({
    status: "not_generated",
    work_item_id: "work_item",
    proposal: null,
    blockers: [],
    safe_next_step: "Wybierz usługę.",
    publish_ready: false
  }),
  getKnowledgeSourceMaterialReadiness: vi.fn()
}));

describe("ContentPlanningGenerationPanel", () => {
  it("shows the real corpus gate without blocking the planning view", async () => {
    vi.mocked(getKnowledgeSourceMaterialReadiness).mockResolvedValue({
      status: "import_pending",
      total_count: 15,
      imported_count: 7,
      import_pending_count: 8,
      excerpt_review_required_count: 0,
      ready_for_generation: false,
      blocker: "Zaimportowano 7 z 15 zatwierdzonych materiałów.",
      next_step: "Kontrolowany import po owner review."
    });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={client}>
        <ContentPlanningGenerationPanel serviceCardId={null} workItemId="work_item" />
      </QueryClientProvider>
    );

    expect(
      await screen.findByTestId("content-material-readiness-warning")
    ).toHaveTextContent("7/15");
    expect(screen.getByText(/plan korzysta wyłącznie z widocznych źródeł/)).toBeInTheDocument();
  });
});
