import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  getContentWorkItemPlanningProposal,
  getKnowledgeSourceMaterialReadiness
} from "../lib/api";
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

  it("does not generate from a recommendation before the marketer confirms the service", async () => {
    vi.mocked(getContentWorkItemPlanningProposal).mockResolvedValueOnce({
      status: "not_generated",
      work_item_id: "work_item",
      proposal: { service_selection_confirmed: false },
      blockers: [],
      safe_next_step: "Potwierdź usługę.",
      publish_ready: false
    } as never);
    vi.mocked(getKnowledgeSourceMaterialReadiness).mockResolvedValueOnce({
      status: "ready",
      total_count: 15,
      imported_count: 15,
      import_pending_count: 0,
      excerpt_review_required_count: 0,
      ready_for_generation: true,
      blocker: null,
      next_step: "Można planować."
    });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={client}>
        <ContentPlanningGenerationPanel
          serviceCardId="service_card"
          workItemId="work_item"
          scopeCurrent
        />
      </QueryClientProvider>
    );

    expect(
      await screen.findByTestId("content-planning-service-confirmation-gate")
    ).toHaveTextContent("Najpierw potwierdź usługę");
    expect(screen.queryByRole("button", { name: "Wygeneruj plan" })).not.toBeInTheDocument();
  });

  it("does not treat a baseline service flag as an approved scope", async () => {
    vi.mocked(getContentWorkItemPlanningProposal).mockResolvedValueOnce({
      status: "not_generated",
      work_item_id: "work_item",
      proposal: { service_selection_confirmed: true },
      blockers: [],
      safe_next_step: "Zatwierdź zakres.",
      publish_ready: false
    } as never);
    vi.mocked(getKnowledgeSourceMaterialReadiness).mockResolvedValueOnce({
      status: "ready",
      total_count: 15,
      imported_count: 15,
      import_pending_count: 0,
      excerpt_review_required_count: 0,
      ready_for_generation: true,
      blocker: null,
      next_step: "Można planować."
    });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={client}>
        <ContentPlanningGenerationPanel
          serviceCardId="service_card"
          workItemId="work_item"
          scopeCurrent={false}
        />
      </QueryClientProvider>
    );

    expect(
      await screen.findByTestId("content-planning-scope-confirmation-gate")
    ).toHaveTextContent("Najpierw zatwierdź zakres");
    expect(screen.queryByRole("button", { name: "Wygeneruj plan" })).not.toBeInTheDocument();
  });
});
