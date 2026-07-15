import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  getContentWorkItemEnrichment,
  getContentWorkItemQueue,
  getContentWorkItemSnapshot,
  getContentWordPressDraftActivationPacket,
  getContentWordPressDraftWriteReadiness,
  getContentWordPressExistingDraftUpdateReadiness,
  getWordPressAuthoringProfile,
  postContentWorkItemQualityReview,
  postContentWorkItemRevisionPlan,
  postContentWorkItemStructuredDraftPreview,
  postContentWorkItemStructuredDraftRuntime,
  postContentWorkItemWordPressAuthoringPayloadPreview,
  postContentWorkItemWordPressDraftExecution,
  saveContentWorkItemDraftRevision,
  saveContentWorkItemDraftRevisionReview,
  saveContentWorkItemSnapshotAudit,
  saveContentWorkItemSnapshotHumanReview,
  type ContentWorkItemQualityReviewResponse,
  type ContentOpportunityEnrichmentResponse,
  type ContentWorkItemQueueResponse,
  type ContentWorkItemRevisionPlanResponse,
  type ContentWorkItemStructuredDraftPreviewResponse,
  type ContentWorkItemStructuredDraftRuntimeResponse,
  type ContentWorkItemWordPressAuthoringPayloadPreviewResponse,
  type ContentWorkItemWordPressDraftExecutionResponse,
  type ContentWorkItemWorkflowSnapshotResponse,
  type ContentWordPressDraftActivationPacketResponse,
  type ContentWordPressDraftWriteReadinessResponse,
  type ContentWordPressExistingDraftUpdateReadinessResponse,
  type WordPressAuthoringProfile
} from "../lib/api";
import type { ContentWorkItem } from "@wilq/shared-schemas";
import { App, createWilqQueryClient, createWilqRouter } from "./App";

vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return {
    ...actual,
    getContentWorkItemEnrichment: vi.fn(),
    getContentWorkItemQueue: vi.fn(),
    getContentWorkItemSnapshot: vi.fn(),
    getContentWordPressDraftActivationPacket: vi.fn(),
    getContentWordPressDraftWriteReadiness: vi.fn(),
    getContentWordPressExistingDraftUpdateReadiness: vi.fn(),
    getWordPressAuthoringProfile: vi.fn(),
    postContentWorkItemQualityReview: vi.fn(),
    postContentWorkItemRevisionPlan: vi.fn(),
    postContentWorkItemStructuredDraftPreview: vi.fn(),
    postContentWorkItemStructuredDraftRuntime: vi.fn(),
    postContentWorkItemWordPressAuthoringPayloadPreview: vi.fn(),
    postContentWorkItemWordPressDraftExecution: vi.fn(),
    saveContentWorkItemDraftRevision: vi.fn(),
    saveContentWorkItemDraftRevisionReview: vi.fn(),
    saveContentWorkItemSnapshotHumanReview: vi.fn(),
    saveContentWorkItemSnapshotAudit: vi.fn()
  };
});

describe("ContentWorkflowSurface", () => {
  beforeEach(() => {
    vi.mocked(getContentWorkItemEnrichment).mockResolvedValue(contentOpportunityEnrichmentResponse());
    vi.mocked(getContentWorkItemQueue).mockResolvedValue(contentQueueResponse());
    vi.mocked(getContentWorkItemSnapshot).mockResolvedValue(workflowSnapshot());
    vi.mocked(getContentWordPressDraftActivationPacket).mockResolvedValue(
      wordpressDraftActivationPacket()
    );
    vi.mocked(getContentWordPressDraftWriteReadiness).mockResolvedValue(
      wordpressDraftWriteReadiness()
    );
    vi.mocked(getContentWordPressExistingDraftUpdateReadiness).mockResolvedValue(
      existingDraftUpdateReadiness()
    );
    vi.mocked(getWordPressAuthoringProfile).mockResolvedValue(wordpressAuthoringProfile());
    vi.mocked(postContentWorkItemQualityReview).mockResolvedValue(qualityReviewResponse());
    vi.mocked(postContentWorkItemRevisionPlan).mockResolvedValue(revisionPlanResponse());
    vi.mocked(saveContentWorkItemSnapshotHumanReview).mockResolvedValue(
      workflowSnapshot({ review: humanReview() }).human_review
    );
    vi.mocked(saveContentWorkItemSnapshotAudit).mockResolvedValue(
      workflowSnapshot({ review: humanReview(), handoff: wordpressHandoff() }).wordpress_handoff
    );
    vi.mocked(postContentWorkItemStructuredDraftRuntime).mockResolvedValue(
      structuredDraftRuntimeResponse()
    );
    vi.mocked(postContentWorkItemStructuredDraftPreview).mockResolvedValue(
      structuredDraftPreviewResponse()
    );
    vi.mocked(postContentWorkItemWordPressAuthoringPayloadPreview).mockResolvedValue(
      wordpressAuthoringPayloadPreviewResponse()
    );
    vi.mocked(postContentWorkItemWordPressDraftExecution).mockResolvedValue(
      wordpressDraftExecutionResponse()
    );
    const revision = savedDraftRevision();
    const workspace = savedRevisionWorkspace(revision);
    vi.mocked(saveContentWorkItemDraftRevision).mockResolvedValue({
      status: "created",
      revision,
      workspace
    });
    const review = savedDraftRevisionReview(revision);
    vi.mocked(saveContentWorkItemDraftRevisionReview).mockResolvedValue({
      status: "recorded",
      review,
      workspace: { ...workspace, status: "approved", latest_review: review, can_review: false }
    });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("shows one API-owned marketer step and keeps technical audit out of the journey", async () => {
    const client = createWilqQueryClient({
      defaultOptions: { queries: { retry: false } }
    });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    const taskMap = await screen.findByTestId(
      "content-workflow-task-map",
      {},
      { timeout: 3_000 }
    );
    const marketerJourney = screen.getByTestId("content-workflow-marketer-journey");
    expect(within(taskMap).getAllByRole("button")).toHaveLength(5);
    expect(within(taskMap).getAllByRole("button").filter(
      (button) => button.getAttribute("aria-current") === "step"
    )).toHaveLength(1);
    expect(within(taskMap).getByRole("button", { name: /Szkic treści/ })).toHaveAttribute(
      "aria-current",
      "step"
    );
    expect(within(taskMap).getByRole("button", { name: /Sprawdzenie treści/ })).toBeDisabled();
    expect(within(taskMap).getByRole("button", { name: /Szkic na devie/ })).toBeDisabled();

    expect(within(marketerJourney).getByText("BDO dla firm")).toBeInTheDocument();
    expect(
      within(marketerJourney).getByText("BDO i sprawozdawczość środowiskowa")
    ).toBeInTheDocument();
    expect(within(marketerJourney).getByText("odśwież istniejącą treść")).toBeInTheDocument();
    expect(within(taskMap).getByText("Brakuje zapisanej wersji szkicu")).toBeInTheDocument();
    expect(within(taskMap).getByText(/Przygotuj podgląd/)).toBeInTheDocument();

    expect(screen.getByTestId("content-workflow-marketer-journey")).toBeInTheDocument();
    expect(screen.queryByTestId("content-workflow-technical-audit")).not.toBeInTheDocument();
    expect(screen.queryByText("Decyzje operatora")).not.toBeInTheDocument();
    expect(document.querySelector('[data-active-workspace="draft"]')).toBeInTheDocument();
    expect(screen.getByText("Tekst sekcji do szkicu")).toBeInTheDocument();
    expect(screen.getByText("Szkic nie ma jeszcze zapisanej wersji")).toBeInTheDocument();
    expect(screen.queryByText("Wersja 1")).not.toBeInTheDocument();
    expect(within(screen.getByTestId("draft-section-tabs")).getAllByRole("button"))
      .toHaveLength(5);
    expect(screen.queryByText("Aktualna strona")).not.toBeInTheDocument();

    fireEvent.click(within(taskMap).getByRole("button", { name: /Plan sekcji/ }));

    expect(document.querySelector('[data-active-workspace="section_map"]')).toBeInTheDocument();
    expect(screen.getByText("Aktualna strona")).toBeInTheDocument();
    expect(screen.getByText("Sygnały i braki")).toBeInTheDocument();
    expect(screen.getByText("Dev draft / ACF")).toBeInTheDocument();
    expect(screen.queryByText("Tekst sekcji do szkicu")).not.toBeInTheDocument();
    expect(within(taskMap).getByRole("button", { name: /Szkic treści/ })).toHaveAttribute(
      "aria-current",
      "step"
    );
    expect(within(taskMap).getByText(/Oglądasz ukończony krok/)).toBeInTheDocument();

    expect(saveContentWorkItemSnapshotHumanReview).not.toHaveBeenCalled();
    expect(saveContentWorkItemSnapshotAudit).not.toHaveBeenCalled();
    expect(postContentWorkItemStructuredDraftRuntime).not.toHaveBeenCalled();
    expect(postContentWorkItemStructuredDraftPreview).not.toHaveBeenCalled();
    expect(postContentWorkItemWordPressDraftExecution).not.toHaveBeenCalled();
    expect(saveContentWorkItemDraftRevision).not.toHaveBeenCalled();
    expect(saveContentWorkItemDraftRevisionReview).not.toHaveBeenCalled();
  });

  it("hydrates a saved revision and creates a child from the exact base", async () => {
    const revision = savedDraftRevision();
    vi.mocked(getContentWorkItemSnapshot).mockResolvedValue(
      workflowSnapshot({ workspace: needsChangesRevisionWorkspace(revision) })
    );
    const client = createWilqQueryClient({
      defaultOptions: { queries: { retry: false } }
    });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    const sectionInput = await screen.findByLabelText("Tekst sekcji Kogo dotyczy BDO");
    expect(sectionInput).toHaveValue("Zapisana treść pierwszej wersji o obowiązkach BDO.");
    const editedBody = "Poprawiona treść drugiej wersji zachowana przez workspace.";
    fireEvent.change(sectionInput, { target: { value: editedBody } });
    fireEvent.click(screen.getByRole("button", { name: "Zapisz wersję do review" }));

    await waitFor(() => expect(saveContentWorkItemDraftRevision).toHaveBeenCalledTimes(1));
    expect(vi.mocked(saveContentWorkItemDraftRevision).mock.calls[0]).toEqual([
      expect.objectContaining({
        base_revision_id: revision.revision_id,
        title: revision.title,
        created_by: "wilku",
        sections: expect.arrayContaining([
          expect.objectContaining({
            heading: "Kogo dotyczy BDO",
            body_markdown: editedBody,
            evidence_ids: ["ev_gsc_bdo"]
          })
        ])
      }),
      revision.work_item_id
    ]);
    await waitFor(() => expect(getContentWorkItemSnapshot).toHaveBeenCalledTimes(2));
    expect(postContentWorkItemWordPressDraftExecution).not.toHaveBeenCalled();
    expect(postContentWorkItemWordPressAuthoringPayloadPreview).not.toHaveBeenCalled();
    expect(saveContentWorkItemSnapshotHumanReview).not.toHaveBeenCalled();
  });

  it("preserves unsaved text when the server rejects a stale base", async () => {
    const revision = savedDraftRevision();
    vi.mocked(getContentWorkItemSnapshot).mockResolvedValue(
      workflowSnapshot({ workspace: needsChangesRevisionWorkspace(revision) })
    );
    vi.mocked(saveContentWorkItemDraftRevision).mockResolvedValue({
      status: "conflict",
      code: "stale_base",
      current_revision_id: "content_revision_bdo_2",
      current_digest: "b".repeat(64),
      safe_next_step: "Porównaj wersję 2 i scal zmiany ręcznie."
    });
    const client = createWilqQueryClient({
      defaultOptions: { queries: { retry: false } }
    });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    const sectionInput = await screen.findByLabelText("Tekst sekcji Kogo dotyczy BDO");
    const localText = "Moje lokalne poprawki nie mogą zniknąć po konflikcie.";
    fireEvent.change(sectionInput, { target: { value: localText } });
    fireEvent.click(screen.getByRole("button", { name: "Zapisz wersję do review" }));

    const conflict = await screen.findByTestId("save-revision-conflict");
    expect(conflict).toHaveTextContent("Twój tekst pozostał w edytorze");
    expect(conflict).toHaveTextContent("Porównaj wersję 2 i scal zmiany ręcznie");
    expect(sectionInput).toHaveValue(localText);
    expect(getContentWorkItemSnapshot).toHaveBeenCalledTimes(1);
    expect(postContentWorkItemWordPressDraftExecution).not.toHaveBeenCalled();
    expect(saveContentWorkItemSnapshotHumanReview).not.toHaveBeenCalled();
  });

  it("blocks save instead of dropping an emptied planned section", async () => {
    const client = createWilqQueryClient({
      defaultOptions: { queries: { retry: false } }
    });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    const sectionInput = await screen.findByLabelText("Tekst sekcji Kogo dotyczy BDO");
    fireEvent.change(sectionInput, { target: { value: "" } });

    expect(screen.getByText(/Każda zaplanowana sekcja musi zachować treść/))
      .toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Zapisz wersję do review" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Sprawdź tekst szkicu" })).toBeDisabled();
    expect(within(screen.getByTestId("draft-section-tabs")).getAllByRole("button"))
      .toHaveLength(5);
    expect(saveContentWorkItemDraftRevision).not.toHaveBeenCalled();
    expect(postContentWorkItemWordPressDraftExecution).not.toHaveBeenCalled();
  });

  it("records an approved decision for the exact revision ID and digest", async () => {
    const revision = savedDraftRevision();
    vi.mocked(getContentWorkItemSnapshot).mockResolvedValue(
      workflowSnapshot({
        workspace: savedRevisionWorkspace(revision),
        currentStepId: "review",
        steps: operatorStepsAtReview()
      })
    );
    const client = createWilqQueryClient({
      defaultOptions: { queries: { retry: false } }
    });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    expect(await screen.findByText(`Wersja ${revision.revision_number}: ${revision.title}`))
      .toBeInTheDocument();
    const immutableContent = screen.getByTestId("immutable-revision-content");
    expect(within(immutableContent).getByText(revision.sections[0]?.body_markdown ?? ""))
      .toBeInTheDocument();
    expect(within(immutableContent).getAllByText(/ev_gsc_bdo/).length).toBeGreaterThan(0);
    expect(
      screen.getByRole("button", {
        name: `Zapisz decyzję dla wersji ${revision.revision_number}`
      })
    ).toBeDisabled();
    expect(screen.getByText(/Dodaj krótką notatkę/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Decyzja dla wersji szkicu"), {
      target: { value: "approved" }
    });
    const approveButton = screen.getByRole("button", {
      name: `Zapisz decyzję dla wersji ${revision.revision_number}`
    });
    expect(approveButton).toBeDisabled();
    fireEvent.click(screen.getByRole("checkbox", { name: "Przeczytano dokładną treść tej wersji." }));
    expect(approveButton).toBeDisabled();
    fireEvent.click(
      screen.getByRole("checkbox", {
        name: "Sprawdzono dowody przypisane do tej wersji."
      })
    );
    expect(approveButton).toBeEnabled();
    fireEvent.click(approveButton);

    await waitFor(() =>
      expect(saveContentWorkItemDraftRevisionReview).toHaveBeenCalledTimes(1)
    );
    expect(vi.mocked(saveContentWorkItemDraftRevisionReview).mock.calls[0]).toEqual([
      {
        expected_revision_digest: revision.content_digest,
        reviewed_by: "wilku",
        decision: "approved",
        notes: "",
        checked_items: [
          "Przeczytano dokładną treść tej wersji.",
          "Sprawdzono dowody przypisane do tej wersji."
        ],
        evidence_ids: uniqueTestEvidence(revision)
      },
      revision.work_item_id,
      revision.revision_id
    ]);
    expect(postContentWorkItemWordPressDraftExecution).not.toHaveBeenCalled();
    expect(postContentWorkItemWordPressAuthoringPayloadPreview).not.toHaveBeenCalled();
    expect(saveContentWorkItemSnapshotHumanReview).not.toHaveBeenCalled();
  });

  it("switches between marketer mode and technical audit mode", async () => {
    const client = createWilqQueryClient({
      defaultOptions: { queries: { retry: false } }
    });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    expect(await screen.findByRole("button", { name: "Marketer" })).toHaveAttribute(
      "aria-pressed",
      "true"
    );
    expect(screen.getByText("Decyzja, blocker i następny bezpieczny krok.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Audyt techniczny" }));
    expect(screen.getByRole("button", { name: "Audyt techniczny" })).toHaveAttribute(
      "aria-pressed",
      "true"
    );
    expect(screen.getByText("Dowody, audyt i kontrakty do sprawdzenia technicznego.")).toBeInTheDocument();
    expect(screen.getByTestId("content-workflow-technical-audit")).toBeInTheDocument();
    expect(screen.queryByTestId("content-workflow-marketer-journey")).not.toBeInTheDocument();
    expect(screen.getByText("Workflow treści: jeden aktywny krok")).toBeInTheDocument();
  });

  it("keeps the queue decision visible while the selected workflow snapshot loads", async () => {
    let resolveSnapshot: ((value: ContentWorkItemWorkflowSnapshotResponse) => void) | undefined;
    vi.mocked(getContentWorkItemSnapshot).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveSnapshot = resolve;
        })
    );
    const client = createWilqQueryClient({
      defaultOptions: { queries: { retry: false } }
    });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    await waitFor(() => {
      expect(getContentWorkItemSnapshot).toHaveBeenCalledWith("content_work_item_bdo");
    });
    expect(screen.getByText("Workflow treści bez slopu")).toBeInTheDocument();
    expect(screen.getAllByText("BDO dla firm").length).toBeGreaterThan(0);
    expect(screen.getByText("Ładowanie szczegółów workflow")).toBeInTheDocument();
    expect(screen.queryByText("Ładowanie stanu WILQ")).not.toBeInTheDocument();

    resolveSnapshot?.(workflowSnapshot());
    expect(await screen.findByTestId("content-workflow-task-map")).toBeInTheDocument();
  });

  it("does not expose the legacy draft-package approval control", async () => {
    const client = createWilqQueryClient({
      defaultOptions: { queries: { retry: false } }
    });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    await openWorkflowDetails();
    expect(screen.queryByRole("button", { name: "Zatwierdź sprawdzenie" }))
      .not.toBeInTheDocument();
    expect(saveContentWorkItemSnapshotAudit).not.toHaveBeenCalled();
    expect(saveContentWorkItemSnapshotHumanReview).not.toHaveBeenCalled();
    expect(postContentWorkItemStructuredDraftRuntime).not.toHaveBeenCalled();
    expect(postContentWorkItemStructuredDraftPreview).not.toHaveBeenCalled();
    expect(postContentWorkItemWordPressDraftExecution).not.toHaveBeenCalled();
  });

  it("does not expose the legacy package-bound audit control", async () => {
    vi.mocked(getContentWorkItemSnapshot).mockResolvedValue(workflowSnapshot({ review: humanReview() }));
    const client = createWilqQueryClient({
      defaultOptions: { queries: { retry: false } }
    });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    await openWorkflowDetails();
    expect(screen.queryByRole("button", { name: "Zapisz audyt przekazania" }))
      .not.toBeInTheDocument();
    expect(saveContentWorkItemSnapshotHumanReview).not.toHaveBeenCalled();
    expect(postContentWorkItemStructuredDraftRuntime).not.toHaveBeenCalled();
    expect(postContentWorkItemStructuredDraftPreview).not.toHaveBeenCalled();
    expect(postContentWorkItemWordPressDraftExecution).not.toHaveBeenCalled();
  });

  it("checks structured draft readiness without live generation or raw payload display", async () => {
    const client = createWilqQueryClient({
      defaultOptions: { queries: { retry: false } }
    });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    await openWorkflowDetails();
    await screen.findByRole("button", { name: "Sprawdź gotowość szkicu" });
    fireEvent.click(screen.getByRole("button", { name: "Sprawdź gotowość szkicu" }));

    await waitFor(() => {
      expect(postContentWorkItemStructuredDraftRuntime).toHaveBeenCalled();
    });
    expect(vi.mocked(postContentWorkItemStructuredDraftRuntime).mock.calls[0]?.[0]).toEqual({
      contract: structuredDraftGenerationContract(),
      model: "gpt-5",
      mode: "dry_run"
    });
    expect(await screen.findByRole("button", { name: "Próba szkicu gotowa" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Pokaż podgląd treści" })).toBeDisabled();
    expect(screen.getByText(/Sama próba gotowości nie tworzy treści/)).toBeInTheDocument();
    expect(screen.getByText(/Próba gotowa/)).toBeInTheDocument();
    expect(screen.getByText(/nie wygenerował treści na żywo/)).toBeInTheDocument();
    expect(screen.queryByText("json_schema")).not.toBeInTheDocument();
    expect(screen.queryByText("responses.create")).not.toBeInTheDocument();
    expect(postContentWorkItemStructuredDraftPreview).not.toHaveBeenCalled();
    expect(postContentWorkItemWordPressDraftExecution).not.toHaveBeenCalled();
  });

  it("shows a structured draft preview only after generated text exists", async () => {
    vi.mocked(postContentWorkItemStructuredDraftRuntime).mockResolvedValue(
      structuredDraftRuntimeResponse({ output: structuredDraftOutput(), status: "generated" })
    );
    const client = createWilqQueryClient({
      defaultOptions: { queries: { retry: false } }
    });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    await openWorkflowDetails();
    await screen.findByRole("button", { name: "Sprawdź gotowość szkicu" });
    fireEvent.click(screen.getByRole("button", { name: "Sprawdź gotowość szkicu" }));

    await screen.findByRole("button", { name: "Próba szkicu gotowa" });
    expect(screen.getByRole("button", { name: "Pokaż podgląd treści" })).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: "Pokaż podgląd treści" }));

    await waitFor(() => {
      expect(postContentWorkItemStructuredDraftPreview).toHaveBeenCalled();
    });
    expect(vi.mocked(postContentWorkItemStructuredDraftPreview).mock.calls[0]?.[0]).toEqual({
      contract: structuredDraftGenerationContract(),
      output: structuredDraftOutput()
    });
    expect(await screen.findByRole("button", { name: "Podgląd treści gotowy" })).toBeDisabled();
    expect(screen.getByText("BDO dla firm - szkic do sprawdzenia")).toBeInTheDocument();
    expect(screen.getAllByText("Kogo dotyczy BDO").length).toBeGreaterThan(0);
    expect(screen.getByText(/Sprawdź z ekspertem, czy opis obowiązku BDO jest aktualny/))
      .toBeInTheDocument();
    expect(screen.getByText(/WordPress i publikacja nadal są zablokowane/)).toBeInTheDocument();
    expect(screen.queryByText("json_schema")).not.toBeInTheDocument();
    expect(screen.queryByText("responses.create")).not.toBeInTheDocument();
    expect(postContentWorkItemWordPressDraftExecution).not.toHaveBeenCalled();
  });

  it("shows API-owned blockers when a queue candidate cannot enter the gated workflow", async () => {
    const client = createWilqQueryClient({
      defaultOptions: { queries: { retry: false } }
    });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    await openWorkflowDetails();
    await screen.findByText("Luka Ahrefs bez finalnego adresu");
    fireEvent.click(screen.getByRole("button", { name: /Luka Ahrefs bez finalnego adresu/ }));

    expect(await screen.findByText("WILQ blokuje pisanie tego tematu")).toBeInTheDocument();
    expect(screen.getAllByText(/Nie można przygotować workflow bez finalnego adresu/)[0])
      .toBeInTheDocument();
    expect(screen.getByText(/Uzupełnij publiczny adres docelowy/)).toBeInTheDocument();
    expect(screen.getByText("zablokuj pisanie")).toBeInTheDocument();
    expect(screen.getByText("pomiar zablokowany")).toBeInTheDocument();
  });

  it("runs quality review and a bounded revision plan after generated content exists", async () => {
    vi.mocked(postContentWorkItemStructuredDraftRuntime).mockResolvedValue(
      structuredDraftRuntimeResponse({ output: structuredDraftOutput(), status: "generated" })
    );
    const client = createWilqQueryClient({
      defaultOptions: { queries: { retry: false } }
    });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    await openWorkflowDetails();
    await screen.findByRole("button", { name: "Sprawdź gotowość szkicu" });
    fireEvent.click(screen.getByRole("button", { name: "Sprawdź gotowość szkicu" }));
    expect(await screen.findByRole("button", { name: "Sprawdź jakość szkicu" })).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: "Sprawdź jakość szkicu" }));

    await waitFor(() => {
      expect(postContentWorkItemQualityReview).toHaveBeenCalled();
    });
    expect(vi.mocked(postContentWorkItemQualityReview).mock.calls[0]?.[0]).toEqual({
      item: workItem(),
      draft_package: draftPackage(),
      structured_output: structuredDraftOutput(),
      claim_ledger: claimLedger(),
      sales_brief: salesBrief(),
      duplicate_risk: "clear"
    });
    expect(await screen.findByRole("button", { name: "Ocena jakości gotowa" })).toBeDisabled();
    expect(screen.getByText("Wzmocnij CTA")).toBeInTheDocument();
    expect(screen.getByText(/Szkic mówi, co zrobić dalej/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Pokaż plan poprawki" })).toBeEnabled();

    fireEvent.click(screen.getByRole("button", { name: "Pokaż plan poprawki" }));
    await waitFor(() => {
      expect(postContentWorkItemRevisionPlan).toHaveBeenCalled();
    });
    expect(vi.mocked(postContentWorkItemRevisionPlan).mock.calls[0]?.[0]).toEqual({
      item: workItem(),
      quality_review: qualityReviewResponse().quality_review
    });
    expect(await screen.findByRole("button", { name: "Plan poprawki gotowy" })).toBeDisabled();
    expect(screen.getByText("Dopisz konkretny następny krok dla klienta")).toBeInTheDocument();
    expect(screen.getByText(/Połącz CTA z usługą Ekologus/)).toBeInTheDocument();
  });

  it("shows dry-run ACF field mapping after the WordPress handoff exists", async () => {
    vi.mocked(getContentWorkItemSnapshot).mockResolvedValue(
      workflowSnapshot({ review: humanReview(), handoff: wordpressHandoff() })
    );
    const client = createWilqQueryClient({
      defaultOptions: { queries: { retry: false } }
    });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    await openWorkflowDetails();
    await screen.findByRole("button", { name: "Pokaż mapowanie ACF" });
    fireEvent.click(screen.getByRole("button", { name: "Pokaż mapowanie ACF" }));

    await waitFor(() => {
      expect(postContentWorkItemWordPressAuthoringPayloadPreview).toHaveBeenCalled();
    });
    expect(vi.mocked(postContentWorkItemWordPressAuthoringPayloadPreview).mock.calls[0]?.[0])
      .toEqual({
        handoff: wordpressHandoff(),
        draft_package: draftPackage(),
        authoring_profile: wordpressAuthoringProfile()
      });
    expect(await screen.findByRole("button", { name: "Mapowanie ACF gotowe" })).toBeDisabled();
    expect(screen.getByText(/layoutu Podstrona/)).toBeInTheDocument();
    expect(screen.getAllByText("Wybrany layout").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Podstrona (podstrona)").length).toBeGreaterThan(0);
    expect(screen.getByText("Mapowanie pól ACF")).toBeInTheDocument();
    expect(screen.getAllByText("Tytuł (tytul)").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Główny opis (glowny_opis)").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Lead (lead)").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Elementy (elementy)").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Kandydat wiersza ACF/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Wiersz do ręcznego przeglądu: Kogo dotyczy BDO/).length)
      .toBeGreaterThan(0);
    expect(screen.getAllByText(/Dowody: ev_gsc_bdo/).length).toBeGreaterThan(0);
    expect(
      screen.getAllByText(/wybór layoutu\/wierszy wymaga osobnego ręcznego przeglądu/).length
    ).toBeGreaterThan(0);
    expect(screen.getByText(/Publikacja i nadpisywanie pozostają zablokowane/))
      .toBeInTheDocument();
    expect(postContentWorkItemWordPressDraftExecution).not.toHaveBeenCalled();
  });

  it("prepares a draft-only WordPress dry-run after handoff", async () => {
    vi.mocked(getContentWorkItemSnapshot).mockResolvedValue(
      workflowSnapshot({ review: humanReview(), handoff: wordpressHandoff() })
    );
    const client = createWilqQueryClient({
      defaultOptions: { queries: { retry: false } }
    });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    await openWorkflowDetails();
    expect(screen.queryByRole("button", { name: "Sprawdzenie zapisane" }))
      .not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Audyt zapisany" })).not.toBeInTheDocument();
    expect(screen.getByText(/Handoff przygotowuje tylko szkic/))
      .toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Sprawdź podgląd szkicu" }));

    await waitFor(() => {
      expect(postContentWorkItemWordPressDraftExecution).toHaveBeenCalled();
    });
    expect(vi.mocked(postContentWorkItemWordPressDraftExecution).mock.calls[0]?.[0]).toEqual({
      handoff: wordpressHandoff(),
      draft_package: draftPackage(),
      mode: "dry_run",
      write_authorization: null
    });
    expect(await screen.findByRole("button", { name: "Podgląd szkicu gotowy" })).toBeDisabled();
    expect(screen.getByText(/WordPress dostałby status draft/)).toBeInTheDocument();
    expect(screen.getByText(/Publikacja: zablokowana/)).toBeInTheDocument();
    expect(screen.getByText(/Nadpisywanie treści: zablokowane/)).toBeInTheDocument();
  });

  it("keeps the direct WordPress endpoint dry-run when readiness claims a write is available", async () => {
    const authorization = {
      action_id: "act_prepare_wordpress_draft_handoff",
      preview_audit_id: "audit_preview_wordpress_draft",
      review_audit_id: "audit_review_wordpress_draft",
      confirmation_audit_id: "audit_confirm_wordpress_draft",
      confirmed_by: "operator_local_dashboard"
    };
    vi.mocked(getContentWorkItemSnapshot).mockResolvedValue(
      workflowSnapshot({ review: humanReview(), handoff: wordpressHandoff() })
    );
    vi.mocked(getContentWordPressDraftActivationPacket).mockResolvedValue({
      ...wordpressDraftActivationPacket(),
      human_review_ready: true,
      audit_ready: true,
      handoff_ready: true,
      dry_run_ready: true,
      handoff_blockers: [],
      execution_blockers: [],
      activation_missing_readiness_labels: []
    });
    vi.mocked(getContentWordPressDraftWriteReadiness).mockResolvedValue({
      ...wordpressDraftWriteReadiness(),
      ready: true,
      live_write_enabled_by_env: true,
      write_authorization_status: "available",
      suggested_write_authorization: authorization,
      blockers: [],
      missing_audit_event_types: [],
      required_audit_events: [
        {
          event_type: "action_preview_generated",
          label: "Podgląd akcji wygenerowany",
          satisfied: true,
          audit_event_id: authorization.preview_audit_id,
          actor: "operator_local_dashboard"
        },
        {
          event_type: "human_review_*",
          label: "Review człowieka zapisane",
          satisfied: true,
          audit_event_id: authorization.review_audit_id,
          actor: "operator_local_dashboard"
        },
        {
          event_type: "action_apply_confirmed",
          label: "Potwierdzenie operatora zapisane",
          satisfied: true,
          audit_event_id: authorization.confirmation_audit_id,
          actor: "operator_local_dashboard"
        }
      ]
    });
    const client = createWilqQueryClient({
      defaultOptions: { queries: { retry: false } }
    });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    const previewButton = await screen.findByRole("button", {
      name: "Przygotuj podgląd draftu"
    });
    await waitFor(() => expect(previewButton).toBeEnabled());
    fireEvent.click(previewButton);

    await waitFor(() => {
      expect(vi.mocked(postContentWorkItemWordPressDraftExecution).mock.calls[0]?.[0]).toEqual({
        handoff: wordpressHandoff(),
        draft_package: draftPackage(),
        mode: "dry_run",
        write_authorization: null,
        section_overrides: expect.any(Array)
      });
    });
    expect(await screen.findByTestId("draft-preview-feedback")).toHaveTextContent(
      "Podgląd szkicu jest gotowy"
    );
    expect(screen.getByTestId("draft-preview-feedback")).toHaveTextContent(
      "Nic nie zapisano w WordPressie"
    );
    expect(screen.getAllByText(/Ten krok przygotowuje wyłącznie podgląd/).length)
      .toBeGreaterThan(0);
    await openWorkflowDetails();
    expect(screen.getByRole("link", { name: "Otwórz kanoniczną akcję do review" })).toHaveAttribute(
      "href",
      "/actions/act_apply_wordpress_draft_handoff"
    );
    expect(screen.getByText(/Nie wykonuje zapisu ani publikacji/)).toBeInTheDocument();
    expect(
      screen.queryByRole("button", {
        name: /Utwórz (?:(?:szkic|draft).*dev|.*dev.*(?:szkic|draft))/i
      })
    ).not.toBeInTheDocument();
  });

  it("shows marketer-safe failure feedback when the dry-run request fails", async () => {
    vi.mocked(getContentWorkItemSnapshot).mockResolvedValue(
      workflowSnapshot({ review: humanReview(), handoff: wordpressHandoff() })
    );
    vi.mocked(getContentWordPressDraftActivationPacket).mockResolvedValue({
      ...wordpressDraftActivationPacket(),
      human_review_ready: true,
      audit_ready: true,
      handoff_ready: true,
      dry_run_ready: true,
      handoff_blockers: [],
      execution_blockers: [],
      activation_missing_readiness_labels: []
    });
    vi.mocked(postContentWorkItemWordPressDraftExecution).mockRejectedValue(
      new Error("transport failure with technical details")
    );
    const client = createWilqQueryClient({
      defaultOptions: { queries: { retry: false } }
    });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    const previewButton = await screen.findByRole("button", {
      name: "Przygotuj podgląd draftu"
    });
    await waitFor(() => expect(previewButton).toBeEnabled());
    fireEvent.click(previewButton);

    const feedback = await screen.findByTestId("draft-preview-feedback");
    expect(feedback).toHaveAttribute("role", "alert");
    expect(feedback).toHaveTextContent("Nie udało się sprawdzić podglądu");
    expect(feedback).toHaveTextContent("WILQ nie zapisał nic w WordPressie");
    expect(feedback).not.toHaveTextContent("transport failure");
    expect(vi.mocked(postContentWorkItemWordPressDraftExecution).mock.calls[0]?.[0])
      .toEqual(expect.objectContaining({ mode: "dry_run", write_authorization: null }));
  });

  it("disables the primary draft preview when API dry-run readiness is blocked", async () => {
    vi.mocked(getContentWorkItemSnapshot).mockResolvedValue(
      workflowSnapshot({ review: humanReview(), handoff: wordpressHandoff() })
    );
    vi.mocked(getContentWordPressDraftActivationPacket).mockResolvedValue({
      ...wordpressDraftActivationPacket(),
      draft_package_ready: true,
      handoff_ready: true,
      dry_run_ready: false,
      execution_blockers: ["action_apply_required"]
    });
    const client = createWilqQueryClient({
      defaultOptions: { queries: { retry: false } }
    });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    expect(
      await screen.findByRole("button", { name: "Przygotuj podgląd draftu" })
    ).toBeDisabled();
    await openWorkflowDetails();
    expect(screen.getByRole("button", { name: "Sprawdź podgląd draftu" })).toBeDisabled();
    for (const button of screen.getAllByRole("button", { name: "Sprawdź tekst szkicu" })) {
      expect(button).toBeDisabled();
    }
    expect(postContentWorkItemWordPressDraftExecution).not.toHaveBeenCalled();
  });

  it("previews edited section text without requesting a direct WordPress write", async () => {
    vi.mocked(getContentWorkItemSnapshot).mockResolvedValue(
      workflowSnapshot({ review: humanReview(), handoff: wordpressHandoff() })
    );
    vi.mocked(getContentWordPressDraftActivationPacket).mockResolvedValue({
      ...wordpressDraftActivationPacket(),
      human_review_ready: true,
      audit_ready: true,
      handoff_ready: true,
      dry_run_ready: true,
      handoff_blockers: [],
      execution_blockers: [],
      activation_missing_readiness_labels: []
    });
    const client = createWilqQueryClient({
      defaultOptions: { queries: { retry: false } }
    });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    await openWorkflowDetails();
    const editedBody =
      "BDO dotyczy firm, które wprowadzają produkty, opakowania albo odpady do ewidencji.";
    const [sectionInput] = await screen.findAllByLabelText("Tekst sekcji Kogo dotyczy BDO");
    fireEvent.change(sectionInput, { target: { value: editedBody } });
    fireEvent.click(
      screen.getAllByRole("button", {
        name: "Sprawdź tekst szkicu"
      })[0]
    );

    await waitFor(() => {
      expect(vi.mocked(postContentWorkItemWordPressDraftExecution).mock.calls[0]?.[0])
        .toEqual(expect.objectContaining({
          handoff: wordpressHandoff(),
          draft_package: draftPackage(),
          mode: "dry_run",
          write_authorization: null,
          section_overrides: expect.arrayContaining([
            expect.objectContaining({
              heading: "Kogo dotyczy BDO",
              body_markdown: editedBody,
              evidence_ids: ["ev_gsc_bdo"]
            })
          ])
        }));
    });
  });

  it("shows remembered dev WordPress draft from the activation packet", async () => {
    vi.mocked(getContentWorkItemSnapshot).mockResolvedValue(
      workflowSnapshot({ review: humanReview(), handoff: wordpressHandoff() })
    );
    vi.mocked(getContentWordPressDraftActivationPacket).mockResolvedValue({
      ...wordpressDraftActivationPacket(),
      human_review_ready: true,
      audit_ready: true,
      handoff_ready: true,
      dry_run_ready: true,
      handoff_blockers: [],
      execution_blockers: [],
      activation_missing_readiness_labels: [],
      execution_result: wordpressDraftCreatedResponse().execution_result,
      draft_readback: {
        status: "available",
        connector: "wordpress_ekologus",
        wordpress_post_id: "987",
        post_status: "draft",
        title: "BDO dla firm - szkic dev",
        link: "https://ekologus.dev.proudsite.pl/?p=987",
        modified_gmt: "2026-07-07T10:00:00",
        content_summary: "Szkic opisuje obowiązki BDO i prowadzi do konsultacji.",
        content_word_count: 92,
        acf_field_count: 2,
        acf_field_names: ["glowny_opis", "elementy"],
        blockers: []
      }
    });
    const client = createWilqQueryClient({
      defaultOptions: { queries: { retry: false } }
    });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    expect(await screen.findByText("Dev draft odczytany")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Otwórz podgląd na dev" })).toHaveAttribute(
      "href",
      "https://ekologus.dev.proudsite.pl/?p=987"
    );
    await openWorkflowDetails();
    expect(screen.getByText(/Szkic utworzony na devie jako WordPress draft, ID 987/))
      .toBeInTheDocument();
    expect(screen.getByText("Odczyt z dev WordPress")).toBeInTheDocument();
    expect(screen.getAllByText(/BDO dla firm - szkic dev/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Szkic opisuje obowiązki BDO/).length).toBeGreaterThan(0);
    expect(screen.getByText("glowny_opis")).toBeInTheDocument();
    expect(screen.getByText("Plan sekcji i ACF")).toBeInTheDocument();
    expect(screen.getAllByText(/Co to jest BDO/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Kogo dotyczy BDO/).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Przygotuj mapowanie sekcji ACF" }))
      .toBeEnabled();
    expect(postContentWorkItemWordPressDraftExecution).not.toHaveBeenCalled();
  });

  it("prepares ACF mapping from the section writing workbench", async () => {
    vi.mocked(getContentWorkItemSnapshot).mockResolvedValue(
      workflowSnapshot({ review: humanReview(), handoff: wordpressHandoff() })
    );
    const client = createWilqQueryClient({
      defaultOptions: { queries: { retry: false } }
    });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    await openWorkflowDetails();
    const button = await screen.findByRole("button", {
      name: "Przygotuj mapowanie sekcji ACF"
    });
    fireEvent.click(button);

    await waitFor(() => {
      expect(postContentWorkItemWordPressAuthoringPayloadPreview).toHaveBeenCalled();
    });
    expect(vi.mocked(postContentWorkItemWordPressAuthoringPayloadPreview).mock.calls[0]?.[0])
      .toEqual({
        handoff: wordpressHandoff(),
        draft_package: draftPackage(),
        authoring_profile: wordpressAuthoringProfile()
      });
    expect(await screen.findAllByText("Wybrany layout")).not.toHaveLength(0);
    expect(screen.getAllByText("Podstrona (podstrona)").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Tytuł (tytul)").length).toBeGreaterThan(0);
  });
});

async function openWorkflowDetails() {
  fireEvent.click(await screen.findByRole("button", { name: "Audyt techniczny" }));
  await screen.findByText("Decyzje operatora");
}

function workItem(overrides: Partial<ContentWorkItem> = {}): ContentWorkItem {
  return {
    id: "content_work_item_bdo",
    topic: "BDO dla firm",
    source_public_url: "https://ekologus.pl/bdo/",
    final_canonical_url: "https://ekologus.pl/bdo/",
    intended_final_url: "https://ekologus.pl/bdo/",
    preview_url: "https://ekologus.dev.proudsite.pl/bdo/",
    wordpress_title_or_h1: "BDO dla firm",
    wordpress_section_headings: [
      "Co to jest BDO",
      "Kogo dotyczy BDO",
      "Jak Ekologus pomaga w dokumentacji"
    ],
    wordpress_section_count: 3,
    wordpress_section_inventory_status: "available",
    evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
    source_connectors: ["google_search_console", "wordpress_ekologus"],
    inventory_status: "resolved",
    canonical_status: "resolved",
    duplicate_status: "checked",
    preflight_status: "plan_allowed",
    preserve_first_plan_status: "approved",
    sales_brief_status: "approved",
    sales_brief_id: "sales_brief_content_work_item_bdo",
    claim_ledger_status: "approved",
    claim_ledger_id: "claim_ledger_bdo",
    draft_package_status: "ready",
    draft_package_id: "draft_package_content_work_item_bdo",
    human_review_status: "missing",
    human_review_id: null,
    wordpress_handoff_status: "missing",
    wordpress_post_id: null,
    measurement_window_status: "missing",
    measurement_window_id: null,
    audit_status: "missing",
    audit_id: null,
    ...overrides
  };
}

function contentQueueResponse(): ContentWorkItemQueueResponse {
  return {
    queue_status: "ready",
    candidate_count: 3,
    actionable_candidate_count: 2,
    minimum_actionable_candidate_count: 3,
    freshness_assessment: contentFreshnessAssessment(),
    operator_summary:
      "Gotowe do pracy: 2 z 3 tematów. Wybierz stronę z adresem, źródłami i następnym krokiem.",
    candidates: [
      {
        work_item_id: "content_work_item_bdo",
        decision_id: "decision_bdo",
        title: "BDO dla firm",
        topic: "BDO dla firm",
        priority: 1,
        recommended_mode: "refresh",
        recommended_mode_label: "odśwież istniejącą treść",
        status_label: "gotowe do planu",
        reason: "Istniejący adres ma popyt z GSC i powinien zostać odświeżony.",
        evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
        source_connectors: ["google_search_console", "wordpress_ekologus"],
        source_connector_labels: ["Google Search Console", "WordPress Ekologus"],
        action_ids: ["act_prepare_content_refresh_queue"],
        action_summary_label: "1 akcja do sprawdzenia",
        source_public_url: "https://ekologus.pl/bdo/",
        final_canonical_url: "https://ekologus.pl/bdo/",
        intended_final_url: "https://ekologus.pl/bdo/",
        preview_url: "https://ekologus.dev.proudsite.pl/bdo/",
        preflight_status: "plan_allowed",
        preflight_status_label: "można planować",
        duplicate_canonical_risk_summary: "Brama adresu i duplikacji jest sprawdzona.",
        measurement_readiness: {
          status: "ready_to_plan",
          label: "pomiar do zaplanowania",
          reason: "WILQ może przygotować okno pomiaru po szkicu.",
          source_connectors: ["google_search_console"]
        },
        safe_next_step: "Przejdź do workflow wybranego tematu.",
        freshness_assessment: contentFreshnessAssessment(),
        blockers: []
      },
      {
        work_item_id: "content_work_item_green_deal",
        decision_id: "decision_green_deal",
        title: "Zielony Ład dla firm",
        topic: "Zielony Ład dla firm",
        priority: 2,
        recommended_mode: "merge",
        recommended_mode_label: "scal z istniejącą treścią",
        status_label: "gotowe do planu",
        reason: "Temat ma powiązany stary URL i wymaga scalania zamiast duplikacji.",
        evidence_ids: ["ev_gsc_green_deal", "ev_wp_green_deal"],
        source_connectors: ["google_search_console", "wordpress_ekologus"],
        source_connector_labels: ["Google Search Console", "WordPress Ekologus"],
        action_ids: ["act_prepare_content_refresh_queue"],
        action_summary_label: "1 akcja do sprawdzenia",
        source_public_url: "https://ekologus.pl/zielony-lad/",
        final_canonical_url: "https://ekologus.pl/zielony-lad/",
        intended_final_url: "https://ekologus.pl/zielony-lad/",
        preview_url: "https://ekologus.dev.proudsite.pl/zielony-lad/",
        preflight_status: "plan_allowed",
        preflight_status_label: "można planować",
        duplicate_canonical_risk_summary: "Sprawdź podobną istniejącą treść przed szkicem.",
        measurement_readiness: {
          status: "ready_to_plan",
          label: "pomiar do zaplanowania",
          reason: "WILQ może przygotować okno pomiaru po szkicu.",
          source_connectors: ["google_search_console"]
        },
        safe_next_step: "Przejdź do workflow wybranego tematu.",
        freshness_assessment: contentFreshnessAssessment(),
        blockers: []
      },
      {
        work_item_id: "content_work_item_ahrefs_gap",
        decision_id: "decision_ahrefs_gap",
        title: "Luka Ahrefs bez finalnego adresu",
        topic: "Luka Ahrefs bez finalnego adresu",
        priority: 3,
        recommended_mode: "block",
        recommended_mode_label: "zablokuj pisanie",
        status_label: "wymaga sprawdzenia przed pisaniem",
        reason: "Nie można przygotować workflow bez finalnego adresu kanonicznego.",
        evidence_ids: ["ev_ahrefs_gap"],
        source_connectors: ["ahrefs"],
        source_connector_labels: ["Ahrefs"],
        action_ids: [],
        action_summary_label: "brak akcji",
        source_public_url: null,
        final_canonical_url: null,
        intended_final_url: null,
        preview_url: "https://ekologus.dev.proudsite.pl/luka/",
        preflight_status: "blocked",
        preflight_status_label: "zablokowane",
        duplicate_canonical_risk_summary:
          "Brak publicznego adresu blokuje ocenę duplikacji i canonical.",
        measurement_readiness: {
          status: "blocked",
          label: "pomiar zablokowany",
          reason: "Brak publicznego finalnego adresu kanonicznego.",
          source_connectors: []
        },
        safe_next_step: "Uzupełnij publiczny adres docelowy albo zostaw temat w review.",
        freshness_assessment: contentFreshnessAssessment(),
        blockers: [
          {
            code: "missing_final_canonical",
            label: "Brakuje finalnego adresu",
            reason: "Nie można przygotować workflow bez finalnego adresu kanonicznego.",
            next_step: "Uzupełnij publiczny adres docelowy albo zostaw temat w review.",
            decision_id: "decision_ahrefs_gap",
            evidence_ids: ["ev_ahrefs_gap"],
            source_connectors: ["ahrefs"]
          }
        ]
      }
    ],
    blockers: [],
    evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo", "ev_gsc_green_deal", "ev_wp_green_deal"],
    source_connectors: ["google_search_console", "wordpress_ekologus", "ahrefs"]
  };
}

function contentFreshnessAssessment() {
  return {
    state: "fresh" as const,
    state_label: "dane treści świeże",
    checked_at: "2026-07-11T08:00:00Z",
    stale_after_hours: 48,
    requires_refresh: false,
    missing_connector_ids: [],
    blocked_connector_ids: [],
    stale_connector_ids: [],
    connector_labels_requiring_refresh: [],
    summary: "Podstawowe dane treści są świeże.",
    next_step: "Można przejść do decyzji contentowej."
  };
}

function contentOpportunityEnrichmentResponse(): ContentOpportunityEnrichmentResponse {
  return {
    enrichment: {
      id: "content_opportunity_enrichment_content_work_item_bdo",
      work_item_id: "content_work_item_bdo",
      decision_id: "decision_bdo",
      title: "BDO dla firm",
      topic: "BDO dla firm",
      recommended_mode: "refresh" as const,
      recommended_mode_label: "odśwież istniejącą treść",
      status: "ready",
      status_label: "gotowe do pracy nad treścią",
      intent: "informational_service",
      intent_label: "informacyjno-usługowa",
      buyer_problem:
        "Firma chce wiedzieć, czy musi aktualizować obowiązki BDO i co zrobić przed kontaktem z doradcą.",
      buyer_trigger: "Zbliża się termin lub kontrola obowiązków środowiskowych.",
      service_fit: "obsługa środowiskowa Ekologus",
      cta_hypothesis: "Zaproponuj krótką konsultację obowiązków BDO.",
      source_facts: [
        {
          id: "source_fact_decision_bdo_0",
          signal_kind: "gsc_query",
          label: "Popyt z GSC",
          summary: "GSC pokazuje popyt na temat BDO.",
          evidence_ids: ["ev_gsc_bdo"],
          source_connectors: ["google_search_console"]
        }
      ],
      measurement_baseline: {
        status: "ready_to_plan",
        label: "pomiar do zaplanowania",
        reason: "WILQ ma dowody GSC i publiczny adres do baseline.",
        metrics_to_watch: ["GSC clicks", "GSC impressions"],
        source_connectors: ["google_search_console"],
        evidence_ids: ["ev_gsc_bdo"]
      },
      blockers: [],
      evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
      source_connectors: ["google_search_console", "wordpress_ekologus"],
      safe_next_step: "Przejdź do briefu i claim gate."
    },
    blockers: []
  };
}

function inventoryResolution() {
  return {
    status: "resolved",
    recommended_mode: "preserve",
    records: [
      {
        id: "inventory_bdo",
        url: "https://ekologus.pl/bdo/",
        final_canonical_url: "https://ekologus.pl/bdo/",
        intended_final_url: "https://ekologus.pl/bdo/",
        preview_url: "https://ekologus.dev.proudsite.pl/bdo/",
        content_status: "published",
        source_connectors: ["wordpress_ekologus"],
        evidence_ids: ["ev_wp_bdo"],
        title: "BDO dla firm",
        h1: "BDO dla firm",
        topic_tags: ["bdo"]
      }
    ],
    similar_existing_urls: ["https://ekologus.pl/bdo/"],
    blockers: [],
    evidence_ids: ["ev_wp_bdo"],
    source_connectors: ["wordpress_ekologus"],
    next_step: "Zacznij od preserve-first."
  };
}

function preflightVerdict(status: string) {
  return {
    status,
    recommended_mode: "preserve",
    create_allowed: false,
    sales_brief_allowed: status !== "plan_allowed",
    draft_allowed: status === "draft_allowed",
    wordpress_draft_allowed: false,
    final_canonical_url: "https://ekologus.pl/bdo/",
    preview_url: "https://ekologus.dev.proudsite.pl/bdo/",
    similar_existing_urls: ["https://ekologus.pl/bdo/"],
    blockers: [],
    blocked_claims: [],
    evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
    source_connectors: ["google_search_console", "wordpress_ekologus"],
    next_step: "Przejdź do kolejnego kroku."
  };
}

function salesBrief() {
  return {
    id: "sales_brief_content_work_item_bdo",
    work_item_id: "content_work_item_bdo",
    topic: "BDO dla firm",
    operations_context: {
      enrichment_id: "content_opportunity_enrichment_content_work_item_bdo",
      intent_label: "intencja ryzyka lub obowiązku",
      recommended_mode: "refresh" as const,
      safe_next_step: "Przygotuj preserve-first brief.",
      source_fact_ids: ["source_fact_queries_bdo"]
    },
    target_reader: "właściciel firmy",
    buyer_problem: "nie wie, jak podejść do BDO",
    buyer_trigger: "zbliża się kontrola",
    search_intent: "informacyjno-usługowy",
    service_fit: "obsługa środowiskowa",
    source_public_url: "https://ekologus.pl/bdo/",
    final_canonical_url: "https://ekologus.pl/bdo/",
    intended_final_url: "https://ekologus.pl/bdo/",
    preview_url: "https://ekologus.dev.proudsite.pl/bdo/",
    existing_content_plan: "Zacznij od istniejącej treści.",
    h1_direction: "BDO dla firm",
    h2_direction: ["Kogo dotyczy BDO"],
    faq_direction: ["Czy każda firma musi mieć BDO?"],
    cta_direction: "Skontaktuj się z Ekologus.",
    internal_link_direction: ["https://ekologus.pl/kontakt/"],
    source_facts: [
      {
        evidence_id: "ev_gsc_bdo",
        source_connector: "google_search_console",
        summary: "GSC pokazuje popyt na temat BDO."
      }
    ],
    knowledge_card_ids: [
      "ekologus_service_environmental_compliance",
      "ekologus_cta_consultation_without_guarantee",
      "ekologus_evidence_live_connector_requirement"
    ],
    knowledge_constraints: [
      {
        card_id: "ekologus_evidence_live_connector_requirement",
        constraint_type: "evidence_requirement" as const,
        label: "Live evidence i source connector są wymagane",
        reason: "Brak evidence ID oznacza brak rekomendacji.",
        evidence_ids: ["ev_content_service_profile_source_facts"]
      }
    ],
    signal_quality: {
      status: "review_required" as const,
      status_label: "sygnał użyteczny, ale wymaga review",
      reason: "Brief ma ślad dowodowy, ale wiedza nadal wymaga decyzji człowieka.",
      evidence_id_count: 2,
      source_connector_count: 2,
      source_fact_count: 1,
      missing_evidence_count: 0,
      knowledge_constraint_count: 1,
      review_required_knowledge_card_count: 1,
      measurement_baseline_ready: true,
      safe_next_step: "Pokaż brief Wilkowi z ograniczeniami wiedzy."
    },
    forbidden_claims: [],
    missing_evidence: [],
    evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
    source_connectors: ["google_search_console", "wordpress_ekologus"],
    measurement_plan: {
      measurement_window_id: "measurement_window_content_work_item_bdo",
      metrics_to_watch: ["GSC clicks"],
      baseline_source_connectors: ["google_search_console"],
      baseline_evidence_ids: ["ev_gsc_bdo"],
      measurement_readiness_label: "baza pomiaru do zaplanowania",
      measurement_readiness_reason: "WILQ ma bazę planu pomiaru.",
      earliest_verdict_note: "Nie oceniaj przed końcem okna.",
      success_claim_rule: "Nie claimuj sukcesu bez danych."
    },
    human_review_required: true,
    draft_allowed: false
  };
}

function draftPackage() {
  return {
    id: "draft_package_content_work_item_bdo",
    work_item_id: "content_work_item_bdo",
    brief_id: "sales_brief_content_work_item_bdo",
    claim_ledger_id: "claim_ledger_bdo",
    draft_kind: "outline" as const,
    title: "BDO dla firm",
    sections: [
      {
        heading: "Kogo dotyczy BDO",
        purpose: "Wyjaśnić, kiedy firma powinna sprawdzić obowiązki BDO.",
        evidence_ids: ["ev_gsc_bdo"],
        draft_notes: ["Nie obiecuj pełnej zgodności bez sprawdzenia przypadku."]
      },
      {
        heading: "Jak przygotować dokumenty",
        purpose: "Pokazać, jakie informacje firma powinna zebrać przed rozmową z Ekologus.",
        evidence_ids: ["ev_wp_bdo"],
        draft_notes: ["Pisz praktycznie, bez obietnic prawnych."]
      },
      {
        heading: "Najczęstsze pytania firm",
        purpose: "Odpowiedzieć na pytania przed kontaktem z Ekologus.",
        evidence_ids: ["ev_gsc_bdo"],
        draft_notes: ["Nie uogólniaj obowiązków prawnych."]
      },
      {
        heading: "Jak wygląda wsparcie Ekologus",
        purpose: "Pokazać bezpieczny zakres wsparcia bez obietnicy wyniku.",
        evidence_ids: ["ev_wp_bdo"],
        draft_notes: ["Używaj wyłącznie zatwierdzonych twierdzeń usługowych."]
      },
      {
        heading: "Następny krok",
        purpose: "Skierować do właściwego kontaktu.",
        evidence_ids: ["ev_wp_bdo"],
        draft_notes: ["CTA wymaga sprawdzenia przez marketera."]
      }
    ],
    section_to_evidence_map: [
      { section_heading: "Kogo dotyczy BDO", evidence_ids: ["ev_gsc_bdo"] },
      { section_heading: "Jak przygotować dokumenty", evidence_ids: ["ev_wp_bdo"] },
      { section_heading: "Najczęstsze pytania firm", evidence_ids: ["ev_gsc_bdo"] },
      { section_heading: "Jak wygląda wsparcie Ekologus", evidence_ids: ["ev_wp_bdo"] },
      { section_heading: "Następny krok", evidence_ids: ["ev_wp_bdo"] }
    ],
    claims_used: [],
    claims_removed_or_blocked: [],
    human_review_questions: ["Czy to brzmi jak Ekologus?"],
    publish_ready: false
  };
}

function workflowSnapshot({
  review = null,
  handoff = null,
  workspace = revisionWorkspace(),
  currentStepId = "draft",
  steps = operatorSteps()
}: {
  review?: ReturnType<typeof humanReview> | null;
  handoff?: ReturnType<typeof wordpressHandoff> | null;
  workspace?: ContentWorkItemWorkflowSnapshotResponse["revision_workspace"];
  currentStepId?: ContentWorkItemWorkflowSnapshotResponse["current_step_id"];
  steps?: ContentWorkItemWorkflowSnapshotResponse["operator_steps"];
} = {}): ContentWorkItemWorkflowSnapshotResponse {
  const reviewedItem = review
    ? workItem({ human_review_status: "approved", human_review_id: review.id })
    : workItem({ human_review_status: "missing", human_review_id: null });
  return {
    response_type: "workflow_snapshot",
    freshness_assessment: contentFreshnessAssessment(),
    candidate: contentQueueResponse().candidates[0],
    service_profile_context: serviceProfileContext(),
    claim_ledger: claimLedger(),
    preflight: {
      item: workItem(),
      inventory_resolution: inventoryResolution(),
      preflight_verdict: preflightVerdict("plan_allowed")
    },
    sales_brief: {
      item: workItem(),
      inventory_resolution: inventoryResolution(),
      preflight_verdict: preflightVerdict("brief_allowed"),
      sales_brief_result: { brief: salesBrief(), blockers: [] }
    },
    draft_package: {
      item: workItem(),
      inventory_resolution: inventoryResolution(),
      preflight_verdict: preflightVerdict("draft_allowed"),
      sales_brief_result: { brief: salesBrief(), blockers: [] },
      draft_package_result: { draft_package: draftPackage(), blockers: [] }
    },
    structured_generation: {
      item: workItem(),
      structured_generation_result: {
        contract: structuredDraftGenerationContract(),
        blockers: []
      }
    },
    human_review: {
      item: workItem(),
      reviewed_item: reviewedItem,
      review,
      blockers: review
        ? []
        : [
            {
              code: "missing_human_review",
              label: "Brakuje decyzji człowieka",
              reason: "Snapshot nie może udawać zatwierdzonego review.",
              next_step: "Zatwierdź brief, claimy i paczkę szkicu."
            }
          ],
      wordpress_handoff_allowed: Boolean(review)
    },
    wordpress_handoff: {
      item: workItem(),
      handoff_result: {
        handoff,
        blockers: handoff
          ? []
          : [
              {
                code: "missing_human_review",
                label: "Brakuje decyzji człowieka",
                reason: "WordPress handoff nie może ruszyć bez zatwierdzonego human review.",
                next_step: "Zatwierdź szkic i claimy przed handoffem."
              },
              {
                code: "missing_audit",
                label: "Brakuje audytu",
                reason: "Każdy WordPress handoff musi mieć audit envelope.",
                next_step: "Zapisz audit_id, actor, reason, evidence IDs i human_review_id."
              }
            ]
      }
    },
    measurement_window: {
      item: workItem(),
      updated_item: workItem({
        measurement_window_status: "planned",
        measurement_window_id: "measurement_window_content_work_item_bdo"
      }),
      measurement_window_result: { window: measurementWindow(), blockers: [] },
      outcome_blockers: [
        {
          code: "measurement_window_not_ready",
          label: "Nie wolno jeszcze oceniać efektu",
          reason: "Okno obserwacji jeszcze trwa.",
          next_step: "Wróć po earliest_verdict_date."
        }
      ]
    },
    revision_workspace: workspace,
    current_step_id: currentStepId,
    operator_steps: steps
  };
}

function revisionWorkspace(): ContentWorkItemWorkflowSnapshotResponse["revision_workspace"] {
  const source = draftPackage();
  return {
    status: "empty",
    latest_revision: null,
    latest_review: null,
    revision_count: 0,
    context_current: true,
    editor_title: source.title,
    editor_sections: source.sections.map((section) => ({
      heading: section.heading,
      body_markdown: [section.purpose, ...section.draft_notes.map((note) => `- ${note}`)].join(
        "\n\n"
      ),
      evidence_ids: [...section.evidence_ids]
    })),
    can_save: true,
    can_review: false,
    safe_next_step: "Edytuj tekst i zapisz pierwszą wersję do review."
  };
}

function savedDraftRevision(): NonNullable<
  ContentWorkItemWorkflowSnapshotResponse["revision_workspace"]["latest_revision"]
> {
  const workspace = revisionWorkspace();
  return {
    revision_id: "content_revision_bdo_1",
    work_item_id: "content_work_item_bdo",
    revision_number: 1,
    base_revision_id: null,
    content_digest: "a".repeat(64),
    draft_package_id: "draft_package_content_work_item_bdo",
    draft_package_digest: "d".repeat(64),
    final_canonical_url: "https://ekologus.pl/bdo/",
    title: workspace.editor_title,
    sections: workspace.editor_sections.map((section, index) => ({
      ...section,
      body_markdown:
        index === 0 ? "Zapisana treść pierwszej wersji o obowiązkach BDO." : section.body_markdown
    })),
    publish_ready: false,
    created_by: "wilku",
    created_at: "2026-07-14T04:00:00Z"
  };
}

function savedDraftRevisionReview(
  revision: ReturnType<typeof savedDraftRevision>,
  decision: "approved" | "needs_changes" | "rejected" | "deferred" = "approved"
): NonNullable<ContentWorkItemWorkflowSnapshotResponse["revision_workspace"]["latest_review"]> {
  return {
    decision_id: `content_revision_decision_${revision.revision_id}_1`,
    decision_number: 1,
    work_item_id: revision.work_item_id,
    revision_id: revision.revision_id,
    revision_digest: revision.content_digest,
    decision,
    reviewed_by: "wilku",
    notes: decision === "approved" ? "" : "Ta wersja wymaga opisanych poprawek.",
    checked_items: ["Sprawdzono dokładną wersję."],
    evidence_ids: uniqueTestEvidence(revision),
    created_at: "2026-07-14T04:05:00Z"
  };
}

function savedRevisionWorkspace(
  revision: ReturnType<typeof savedDraftRevision>
): ContentWorkItemWorkflowSnapshotResponse["revision_workspace"] {
  return {
    status: "unreviewed",
    latest_revision: revision,
    latest_review: null,
    revision_count: revision.revision_number,
    context_current: true,
    editor_title: revision.title,
    editor_sections: revision.sections,
    can_save: false,
    can_review: true,
    safe_next_step: `Sprawdź dokładną treść wersji ${revision.revision_number}.`
  };
}

function needsChangesRevisionWorkspace(
  revision: ReturnType<typeof savedDraftRevision>
): ContentWorkItemWorkflowSnapshotResponse["revision_workspace"] {
  return {
    ...savedRevisionWorkspace(revision),
    status: "needs_changes",
    latest_review: savedDraftRevisionReview(revision, "needs_changes"),
    can_save: true,
    can_review: false,
    safe_next_step: "Wprowadź poprawki i zapisz kolejną wersję."
  };
}

function operatorStepsAtReview(): ContentWorkItemWorkflowSnapshotResponse["operator_steps"] {
  return operatorSteps().map((step) => {
    if (step.id === "draft") {
      return {
        ...step,
        phase: "complete",
        readiness: "ready",
        status_label: "wersja zapisana",
        blocker: null,
        safe_next_step: "Sprawdź zapisaną wersję."
      };
    }
    if (step.id === "review") {
      return {
        ...step,
        phase: "current",
        readiness: "review_required",
        status_label: "wymaga decyzji",
        can_open: true,
        can_submit: true,
        blocker: null,
        safe_next_step: "Zapisz decyzję dla dokładnej wersji."
      };
    }
    return step;
  });
}

function uniqueTestEvidence(revision: ReturnType<typeof savedDraftRevision>) {
  return [...new Set(revision.sections.flatMap((section) => section.evidence_ids))];
}

function serviceProfileContext() {
  return {
    binding_status: "bound" as const,
    decision_status: "blocked" as const,
    status_label: "Kontekst usługi nie jest zatwierdzony do finalnych treści",
    reason:
      "WILQ dopasował kartę BDO, ale Service Profile nie ma jeszcze zatwierdzenia do production-depth.",
    service_card_id: "ekologus_service_bdo_reporting",
    service_label: "BDO i sprawozdawczość środowiskowa",
    service_status: "source_backed_review_required",
    service_status_label: "źródło istnieje, wymagane review",
    freshness_label: "publiczna strona wymaga review (ostatni sygnał: 2026-07-02)",
    freshness_as_of: "2026-07-02",
    source_summary_label: "Źródło profilu: publiczna strona Ekologus",
    allowed_claims: ["Ekologus może pomóc firmie uporządkować obowiązki BDO."],
    claims_needing_review: ["Potwierdź zakres usługi przed finalnym draftem"],
    blocked_claims: ["Gwarancje efektu są zablokowane"],
    claim_policy_scope_label:
      "Ten skrót dotyczy tylko dopasowanej karty usługi. Pełny rejestr twierdzeń dla szkicu jest niżej.",
    evidence_requirements: ["Dowód bieżący z connectora jest wymagany."],
    missing_contracts: ["Publiczne karty usług sprawdzone przez człowieka"],
    safe_next_step: "Sprawdź kartę usługi BDO przed finalnym draftem.",
    source_connectors: ["public_site"],
    evidence_ids: ["ev_content_service_profile_source_facts"],
    knowledge_card_ids: ["ekologus_service_bdo_reporting"],
    review_action_id: "service_profile_review_card_ekologus_service_bdo_reporting",
    review_action_label: "Sprawdź kartę usługi: BDO i sprawozdawczość środowiskowa"
  };
}

function claimLedger() {
  return {
    id: "claim_ledger_bdo",
    work_item_id: "content_work_item_bdo",
    reviewed_by: "wilku",
    entries: [
      {
        id: "claim_service_bdo",
        claim_text: "Ekologus pomaga firmom uporządkować obowiązki BDO.",
        claim_type: "service_claim" as const,
        status: "allowed_with_evidence" as const,
        strength: "strong" as const,
        required: true,
        evidence_ids: ["ev_wp_bdo"],
        source_connectors: ["wordpress_ekologus"],
        reason: "Twierdzenie ma przypisany dowód źródłowy.",
        reviewer_id: "wilku"
      },
      {
        id: "claim_review_bdo",
        claim_text: "BDO może wiązać się z ryzykiem kary.",
        claim_type: "risk_claim" as const,
        status: "needs_human_review" as const,
        strength: "weak" as const,
        required: false,
        evidence_ids: ["ev_wp_bdo"],
        source_connectors: ["wordpress_ekologus"],
        reason: "Twierdzenie ryzyka wymaga decyzji człowieka.",
        reviewer_id: null
      },
      {
        id: "claim_effect_bdo",
        claim_text: "Odświeżenie treści zwiększy liczbę leadów.",
        claim_type: "business_outcome_claim" as const,
        status: "blocked_until_measurement" as const,
        strength: "strong" as const,
        required: false,
        evidence_ids: [],
        source_connectors: [],
        reason: "Twierdzenie o skuteczności wymaga zakończonego okna pomiaru.",
        reviewer_id: null
      }
    ]
  };
}

function measurementWindow() {
  return {
    id: "measurement_window_content_work_item_bdo",
    work_item_id: "content_work_item_bdo",
    content_url: "https://ekologus.pl/bdo/",
    baseline_period: { start: "2026-05-01", end: "2026-05-31" },
    observation_period: { start: "2026-07-01", end: "2026-07-31" },
    earliest_verdict_date: "2026-08-01",
    allowed_metrics: ["gsc_clicks"],
    source_connectors: ["google_search_console"],
    evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
    status: "planned",
    handoff_id: "wordpress_draft_handoff_content_work_item_bdo",
    success_claim_allowed: false
  };
}

function humanReview() {
  return {
    id: "human_review_content_work_item_bdo",
    work_item_id: "content_work_item_bdo",
    stage: "draft_package",
    reviewed_by: "wilku",
    decision: "approved",
    notes: "Operator zatwierdził paczkę szkicu.",
    checked_items: ["Brief i paczka szkicu są zgodne z dowodami WILQ."],
    evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
    blocked_claims_handled: [],
    draft_package_id: "draft_package_content_work_item_bdo"
  };
}

function wordpressHandoff() {
  return {
    id: "wordpress_draft_handoff_content_work_item_bdo",
    work_item_id: "content_work_item_bdo",
    draft_package_id: "draft_package_content_work_item_bdo",
    human_review_id: "human_review_content_work_item_bdo",
    audit_id: "audit_content_work_item_bdo",
    connector: "wordpress_ekologus" as const,
    operation_type: "create_wordpress_draft" as const,
    status: "prepared" as const,
    post_status: "draft" as const,
    title: "BDO dla firm",
    final_canonical_url: "https://ekologus.pl/bdo/",
    intended_final_url: "https://ekologus.pl/bdo/",
    preview_url: "https://ekologus.dev.proudsite.pl/bdo/",
    evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
    publish_allowed: false,
    destructive_update_allowed: false
  };
}

function structuredDraftGenerationContract() {
  return {
    schema_name: "wilq_content_structured_draft_v1" as const,
    strict_schema: true as const,
    model_input: {
      work_item_id: "content_work_item_bdo",
      language: "pl-PL" as const,
      draft_kind: "section_draft" as const,
      title: "BDO dla firm",
      final_canonical_url: "https://ekologus.pl/bdo/",
      source_public_url: "https://ekologus.pl/bdo/",
      preview_url: "https://ekologus.dev.proudsite.pl/bdo/",
      target_reader: "właściciel firmy",
      buyer_problem: "nie wie, jak podejść do BDO",
      buyer_trigger: "zbliża się kontrola",
      search_intent: "informacyjno-usługowy",
      service_fit: "obsługa środowiskowa",
      cta_direction: "Skontaktuj się z Ekologus.",
      sections: [
        {
          heading: "Kogo dotyczy BDO",
          purpose: "Wyjaśnić, kiedy firma powinna sprawdzić obowiązki BDO.",
          evidence_ids: ["ev_gsc_bdo"],
          draft_notes: ["Nie obiecuj pełnej zgodności bez sprawdzenia przypadku."]
        }
      ],
      source_facts: [
        {
          evidence_id: "ev_gsc_bdo",
          source_connector: "google_search_console",
          summary: "GSC pokazuje popyt na temat BDO."
        }
      ],
      knowledge_constraints: [
        {
          card_id: "ekologus_evidence_live_connector_requirement",
          constraint_type: "evidence_requirement" as const,
          label: "Live evidence i source connector są wymagane",
          reason: "Brak evidence ID oznacza brak rekomendacji.",
          evidence_ids: ["ev_content_service_profile_source_facts"]
        }
      ],
      sales_brief_signal_quality: salesBriefSignalQuality(),
      claims_allowed: [],
      claim_markers: [],
      removed_or_blocked_claim_markers: [],
      claims_removed_or_blocked: [],
      human_review_questions: ["Czy to brzmi jak Ekologus?"]
    },
    output_schema: {
      type: "object",
      additionalProperties: false
    },
    system_instruction: "Pisz wyłącznie z przekazanych faktów.",
    user_instruction: "Przygotuj ustrukturyzowany szkic treści dla WILQ.",
    publish_ready: false as const
  };
}

function salesBriefSignalQuality() {
  return {
    status: "review_required" as const,
    status_label: "sygnał użyteczny, ale wymaga review",
    reason: "Brief ma ślad dowodowy, ale wiedza nadal wymaga decyzji człowieka.",
    evidence_id_count: 2,
    source_connector_count: 2,
    source_fact_count: 1,
    missing_evidence_count: 0,
    knowledge_constraint_count: 1,
    review_required_knowledge_card_count: 1,
    measurement_baseline_ready: true,
    safe_next_step: "Pokaż brief Wilkowi z ograniczeniami wiedzy."
  };
}

function structuredDraftRuntimeResponse({
  output = null,
  status = output ? "generated" : "dry_run_ready",
  externalCallAttempted = Boolean(output)
}: {
  output?: ContentWorkItemStructuredDraftRuntimeResponse["runtime_result"]["output"];
  status?: ContentWorkItemStructuredDraftRuntimeResponse["runtime_result"]["status"];
  externalCallAttempted?: boolean;
} = {}): ContentWorkItemStructuredDraftRuntimeResponse {
  return {
    runtime_result: {
      status,
      request_payload: {
        model: "gpt-5",
        input: [
          {
            role: "system",
            content: "Pisz wyłącznie z przekazanych faktów."
          },
          {
            role: "user",
            content: "Przygotuj ustrukturyzowany szkic treści dla WILQ."
          }
        ],
        text: {
          format: {
            type: "json_schema",
            name: "wilq_content_structured_draft_v1",
            strict: true,
            schema: {
              type: "object",
              additionalProperties: false
            }
          }
        },
        temperature: 0.2,
        max_output_tokens: 4000
      },
      output,
      external_call_attempted: externalCallAttempted,
      blockers: []
    }
  };
}

function structuredDraftOutput() {
  return {
    draft_kind: "section_draft" as const,
    language: "pl-PL" as const,
    title: "BDO dla firm - szkic do sprawdzenia",
    meta_title: "BDO dla firm - szkic",
    meta_description: "Wyjaśnienie obowiązków BDO dla firm na podstawie sprawdzonych źródeł.",
    h1: "BDO dla firm",
    sections: [
      {
        heading: "Kogo dotyczy BDO",
        body_markdown:
          "BDO może dotyczyć firm, które wytwarzają odpady albo wprowadzają produkty w opakowaniach. WILQ wskazuje ten fragment jako szkic do sprawdzenia, nie poradę prawną.",
        evidence_ids: ["ev_gsc_bdo"],
        claims_used: []
      }
    ],
    faq: ["Czy każda firma musi mieć BDO?"],
    cta: "Skontaktuj się z Ekologus i sprawdź obowiązki dla swojej firmy.",
    internal_links: ["https://ekologus.pl/kontakt/"],
    source_facts_used: ["ev_gsc_bdo"],
    claims_needing_review: [],
    forbidden_claims_avoided: ["gwarancja pełnej zgodności z przepisami"],
    human_review_checklist: [
      "Sprawdź z ekspertem, czy opis obowiązku BDO jest aktualny.",
      "Sprawdź, czy CTA pasuje do procesu sprzedaży Ekologus."
    ],
    publish_ready: false as const
  };
}

function structuredDraftPreviewResponse(): ContentWorkItemStructuredDraftPreviewResponse {
  const output = structuredDraftOutput();
  return {
    preview_result: {
      preview: {
        title: output.title,
        meta_title: output.meta_title,
        meta_description: output.meta_description,
        h1: output.h1,
        sections: output.sections,
        faq: output.faq,
        cta: output.cta,
        internal_links: output.internal_links,
        source_facts_used: output.source_facts_used,
        forbidden_claims_avoided: output.forbidden_claims_avoided,
        human_review_checklist: output.human_review_checklist,
        publish_ready: false
      },
      blockers: []
    }
  };
}

function qualityReviewResponse(): ContentWorkItemQualityReviewResponse {
  return {
    item: workItem(),
    quality_review: {
      review_id: "quality_review_content_work_item_bdo",
      work_item_id: "content_work_item_bdo",
      draft_package_id: "draft_package_content_work_item_bdo",
      verdict: "needs_changes",
      evidence_coverage: {
        status: "pass",
        label: "Pokrycie dowodami",
        reason: "Sekcje wskazują dowody WILQ."
      },
      claim_safety: {
        status: "pass",
        label: "Bezpieczeństwo twierdzeń",
        reason: "Szkic nie używa zablokowanych claimów."
      },
      duplicate_risk: {
        status: "pass",
        label: "Ryzyko duplikacji",
        reason: "Wybrany temat odświeża istniejący adres."
      },
      usefulness: {
        status: "needs_changes",
        label: "Użyteczność dla czytelnika",
        reason: "Szkic mówi, co zrobić dalej, ale CTA wymaga doprecyzowania."
      },
      service_fit: {
        status: "pass",
        label: "Dopasowanie do usługi",
        reason: "Treść prowadzi do obsługi środowiskowej Ekologus."
      },
      search_intent_fit: {
        status: "pass",
        label: "Dopasowanie do intencji",
        reason: "Szkic odpowiada na pytanie informacyjno-usługowe."
      },
      buyer_problem_fit: {
        status: "pass",
        label: "Problem kupującego",
        reason: "Szkic odnosi się do niepewności firmy wokół BDO."
      },
      cta_quality: {
        status: "needs_changes",
        label: "Jakość CTA",
        reason: "CTA jest zbyt ogólne i powinno wskazać konkretny następny krok."
      },
      factual_precision: {
        status: "pass",
        label: "Precyzja faktów",
        reason: "Szkic używa tylko przekazanych dowodów."
      },
      polish_language_quality: {
        status: "pass",
        label: "Język polski",
        reason: "Tekst jest po polsku i czytelny."
      },
      internal_link_fit: {
        status: "pass",
        label: "Linkowanie wewnętrzne",
        reason: "Szkic ma link do kontaktu."
      },
      measurement_readiness: {
        status: "pass",
        label: "Gotowość pomiaru",
        reason: "Okno pomiaru jest zaplanowane."
      },
      blockers: [],
      findings: [
        {
          code: "weak_cta",
          severity: "needs_changes",
          label: "Wzmocnij CTA",
          reason: "Szkic mówi, co zrobić dalej, ale wezwanie do kontaktu jest za ogólne.",
          next_step: "Dopisz konkretny następny krok dla klienta.",
          affected_section: "CTA",
          evidence_ids: ["ev_gsc_bdo"],
          source_connectors: ["google_search_console"]
        }
      ],
      revision_instructions: [
        {
          id: "revision_instruction_cta",
          affected_section: "CTA",
          change: "Dopisz konkretny następny krok dla klienta",
          reason: "Połącz CTA z usługą Ekologus i problemem BDO.",
          required_evidence_ids: ["ev_gsc_bdo"],
          forbidden_claims_to_avoid: ["gwarancja pełnej zgodności z przepisami"],
          human_review_checklist_additions: ["Sprawdź, czy CTA pasuje do sprzedaży Ekologus."]
        }
      ],
      evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
      source_connectors: ["google_search_console", "wordpress_ekologus"],
      safe_next_step: "Popraw tylko wskazane CTA i uruchom ocenę jakości ponownie."
    }
  };
}

function revisionPlanResponse(): ContentWorkItemRevisionPlanResponse {
  return {
    item: workItem(),
    revision_plan: {
      id: "revision_plan_content_work_item_bdo",
      work_item_id: "content_work_item_bdo",
      quality_review_id: "quality_review_content_work_item_bdo",
      status: "ready",
      draft_revision_allowed: true,
      instructions: qualityReviewResponse().quality_review.revision_instructions,
      blockers: [],
      evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
      source_connectors: ["google_search_console", "wordpress_ekologus"],
      safe_next_step: "Wykonaj tylko wskazane poprawki i uruchom ocenę jakości ponownie."
    }
  };
}

function wordpressAuthoringPayloadPreviewResponse(): ContentWorkItemWordPressAuthoringPayloadPreviewResponse {
  return {
    authoring_profile: wordpressAuthoringProfile(),
    preview_result: {
      status: "ready",
      mode: "dry_run",
      connector: "wordpress_ekologus",
      endpoint_kind: "posts",
      post_status: "draft",
      flexible_content_field_name: "podstrona",
      sections: [
        {
          layout_name: "podstrona",
          layout_label: "Podstrona",
          section_heading: "Kogo dotyczy BDO",
          field_values: {
            tytul: "Kogo dotyczy BDO",
            glowny_opis:
              "Wyjaśnij, kiedy temat BDO wymaga sprawdzenia z Ekologus i które dowody WILQ używa w szkicu.",
            elementy: null
          },
          field_previews: [
            {
              field_name: "tytul",
              field_label: "Tytuł",
              field_type: "text",
              value_preview: "Kogo dotyczy BDO",
              safe_to_autofill: true,
              note: null,
              nested_values: [],
              row_candidates: []
            },
            {
              field_name: "glowny_opis",
              field_label: "Główny opis",
              field_type: "group",
              value_preview:
                "Wyjaśnij, kiedy temat BDO wymaga sprawdzenia z Ekologus i które dowody WILQ używa w szkicu.",
              safe_to_autofill: true,
              note: "Grupa ACF: WILQ mapuje jej pod pola w podglądzie.",
              nested_values: [
                {
                  field_name: "lead",
                  field_label: "Lead",
                  field_type: "wysiwyg",
                  value_preview: "Wyjaśnij, kiedy temat BDO wymaga sprawdzenia z Ekologus.",
                  safe_to_autofill: true,
                  note: null,
                  nested_values: [],
                  row_candidates: []
                },
                {
                  field_name: "opis",
                  field_label: "Opis",
                  field_type: "wysiwyg",
                  value_preview:
                    "Wyjaśnij, kiedy temat BDO wymaga sprawdzenia z Ekologus i które dowody WILQ używa w szkicu.",
                  safe_to_autofill: true,
                  note: null,
                  nested_values: [],
                  row_candidates: []
                }
              ],
              row_candidates: []
            },
            {
              field_name: "elementy",
              field_label: "Elementy",
              field_type: "flexible_content",
              value_preview: null,
              safe_to_autofill: true,
              note:
                "Pole zagnieżdżone: WILQ pokazuje możliwe mapowanie pod pól, ale wybór layoutu/wierszy wymaga osobnego ręcznego przeglądu.",
              nested_values: [
                {
                  field_name: "opis",
                  field_label: "Opis",
                  field_type: "wysiwyg",
                  value_preview: "Opis sekcji do sprawdzenia.",
                  safe_to_autofill: true,
                  note: null,
                  nested_values: [],
                  row_candidates: []
                }
              ],
              row_candidates: [
                {
                  row_type: "acf_flexible_content_row",
                  row_label: "Wiersz do ręcznego przeglądu: Kogo dotyczy BDO",
                  review_status: "review_required",
                  note:
                    "WILQ proponuje tylko kandydat wiersza ACF do ręcznego przeglądu; nie wybiera finalnego layoutu i nie zapisuje nic w WordPress.",
                  field_values: [
                    {
                      field_name: "opis",
                      field_label: "Opis",
                      field_type: "wysiwyg",
                      value_preview: "Opis sekcji do sprawdzenia.",
                      safe_to_autofill: true,
                      note: null
                    }
                  ],
                  evidence_ids: ["ev_gsc_bdo"]
                }
              ]
            }
          ],
          missing_required_fields: [],
          evidence_ids: ["ev_gsc_bdo"]
        }
      ],
      publish_allowed: false,
      destructive_update_allowed: false,
      external_write_attempted: false,
      required_action_contract: "actionobject_validate_preview_review_confirm_audit",
      blockers: []
    }
  };
}

function wordpressDraftExecutionResponse(): ContentWorkItemWordPressDraftExecutionResponse {
  return {
    execution_result: {
      status: "dry_run_ready",
      mode: "dry_run",
      boundary: {
        allowed_operation: "create_wordpress_draft",
        dry_run_default: true,
        live_write_enabled: false,
        live_adapter_configured: false,
        publish_allowed: false,
        destructive_update_allowed: false
      },
      payload: {
        connector: "wordpress_ekologus",
        endpoint_kind: "posts",
        post_status: "draft",
        title: "BDO dla firm",
        content_markdown: "# BDO dla firm",
        final_canonical_url: "https://ekologus.pl/bdo/",
        evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
        publish_allowed: false,
        destructive_update_allowed: false
      },
      wordpress_post_id: null,
      external_write_attempted: false,
      blockers: []
    }
  };
}

function wordpressDraftCreatedResponse(): ContentWorkItemWordPressDraftExecutionResponse {
  return {
    execution_result: {
      ...wordpressDraftExecutionResponse().execution_result,
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
      wordpress_post_id: "987",
      external_write_attempted: true
    }
  };
}

function wordpressDraftActivationPacket(): ContentWordPressDraftActivationPacketResponse {
  return {
    response_type: "wordpress_draft_activation_packet",
    contract: "wordpress_draft_activation_packet_v1",
    action_id: "act_apply_wordpress_draft_handoff",
    work_item_id: "content_work_item_bdo",
    topic: "SEO: odśwież BDO dla firm",
    final_canonical_url: "https://ekologus.pl/bdo/",
    draft_package_ready: true,
    draft_package_id: "draft_package_content_work_item_bdo",
    review_preview_ready: true,
    review_preview_status_label: "Paczka szkicu jest gotowa do review człowieka.",
    human_review_checklist: [
      "Czy treść brzmi jak Ekologus, a nie jak generyczny artykuł SEO?",
      "Czy materiał ma zostać tylko szkicem WordPress, bez publikacji?"
    ],
    human_review_ready: false,
    audit_ready: false,
    handoff_ready: false,
    handoff_id: null,
    dry_run_ready: false,
    live_write_enabled_by_env: false,
    publish_allowed: false,
    destructive_update_allowed: false,
    external_write_attempted: false,
    handoff_blockers: ["missing_human_review", "missing_audit"],
    execution_blockers: ["missing_handoff"],
    activation_missing_step: "human_review",
    activation_missing_step_label: "zapisz review człowieka",
    activation_missing_readiness_labels: [
      "review człowieka",
      "audit przekazania",
      "handoff WordPress",
      "podgląd dry-run"
    ],
    execution_result: {
      status: "blocked",
      mode: "dry_run",
      boundary: {
        allowed_operation: "create_wordpress_draft",
        dry_run_default: true,
        live_write_enabled: false,
        live_adapter_configured: false,
        publish_allowed: false,
        destructive_update_allowed: false
      },
      payload: null,
      wordpress_post_id: null,
      external_write_attempted: false,
      blockers: [
        {
          code: "missing_handoff",
          label: "Brakuje zatwierdzonego przekazania",
          reason: "Nie można przygotować szkicu WordPress bez zatwierdzonego przekazania.",
          next_step: "Najpierw zatwierdź szkic, zapisz audyt i przygotuj przekazanie."
        }
      ]
    },
    draft_readback: null,
    operator_next_step:
      "Najbliższy krok: zapisz review człowieka dla paczki szkicu. Bez tego WILQ nie przygotuje handoffu ani dry-run payloadu WordPress.",
    next_steps: [
      "Utrzymaj zakres WordPress draft-only: bez publikacji i bez aktualizacji istniejących wpisów.",
      "Zapisz human review dla tej paczki szkicu.",
      "Zapisz audit przekazania do WordPress po review.",
      "Wróć do handoffu i dopiero potem sprawdź dry-run execution."
    ],
    evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
    source_connectors: ["google_search_console", "wordpress_ekologus"]
  };
}

function wordpressDraftWriteReadiness(): ContentWordPressDraftWriteReadinessResponse {
  return {
    response_type: "wordpress_draft_write_readiness",
    contract: "wordpress_draft_write_readiness_v1",
    connector: "wordpress_ekologus",
    action_id: "act_prepare_wordpress_draft_handoff",
    ready: false,
    live_write_enabled_by_env: false,
    rest_adapter_configured: true,
    publish_allowed: false,
    destructive_update_allowed: false,
    required_audit_events: [
      {
        event_type: "action_preview_generated",
        label: "Podgląd akcji wygenerowany",
        satisfied: false,
        audit_event_id: null,
        actor: null
      },
      {
        event_type: "human_review_*",
        label: "Review człowieka zapisane",
        satisfied: false,
        audit_event_id: null,
        actor: null
      },
      {
        event_type: "action_apply_confirmed",
        label: "Potwierdzenie operatora zapisane",
        satisfied: false,
        audit_event_id: null,
        actor: null
      }
    ],
    missing_audit_event_types: [
      "action_preview_generated",
      "human_review_*",
      "action_apply_confirmed"
    ],
    write_authorization_status: "missing_audit_trace",
    suggested_write_authorization: null,
    blockers: [
      {
        code: "draft_writes_env_disabled",
        label: "Zapis szkiców WordPress jest wyłączony",
        reason:
          "WILQ może przygotować i sprawdzić szkic, ale live write wymaga jawnego włączenia WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES.",
        next_step:
          "Zostaw tryb dry-run albo włącz env dopiero po potwierdzeniu ścieżki preview, review, confirm i audit."
      },
      {
        code: "wordpress_rest_adapter_not_configured",
        label: "Adapter REST WordPress nie jest gotowy",
        reason: "Brakuje kompletnej konfiguracji REST.",
        next_step: "Uzupełnij REST adapter przed powrotem do live write."
      }
    ],
    operator_next_step:
      "Zostaw tryb dry-run albo włącz env dopiero po potwierdzeniu ścieżki preview, review, confirm i audit.",
    evidence_ids: ["ev_connector_wordpress_ekologus_status"],
    source_connectors: ["wordpress_ekologus"]
  };
}

function existingDraftUpdateReadiness(): ContentWordPressExistingDraftUpdateReadinessResponse {
  return {
    response_type: "wordpress_existing_draft_update_readiness",
    contract: "wordpress_existing_draft_update_readiness_v1",
    connector: "wordpress_ekologus",
    action_id: "act_prepare_wordpress_existing_draft_update",
    work_item_id: "content_work_item_bdo",
    target_post_id: "2",
    target_url: "https://ekologus.dev.proudsite.pl/",
    current_state_available: true,
    current_section_count: 9,
    proposed_section_count: 3,
    ready: false,
    update_supported: false,
    publish_allowed: false,
    destructive_update_allowed: false,
    blockers: [
      {
        code: "existing_draft_update_contract_not_implemented",
        label: "Aktualizacja istniejącego draftu wymaga osobnego kontraktu",
        reason: "Preview only",
        next_step: "Review first"
      }
    ],
    operator_next_step: "Review first",
    evidence_ids: ["ev_wp_bdo"],
    source_connectors: ["wordpress_ekologus"],
    section_diff_preview: [
      {
        heading: "Wprowadzenie",
        current_summary: "Aktualny tekst dev",
        proposed_summary: "Proponowany tekst szkicu",
        status: "changed"
      }
    ]
  };
}

function wordpressAuthoringProfile(): WordPressAuthoringProfile {
  return {
    profile_version: "wordpress_authoring_profile_v1",
    connector: "wordpress_ekologus",
    site_kind: "primary",
    authoring_target: "staging",
    discovery_mode: "rest_first",
    discovery_order: ["rest", "acf_rest", "wp_cli", "helper"],
    rest_api: {
      method: "rest",
      status: "configured",
      base_url_configured: true,
      auth_configured: true,
      public_url_configured: true,
      post_types: ["page", "post"]
    },
    acf: {
      enabled_state: "unknown",
      rest_enabled_state: "unknown",
      flexible_content_field_name: null,
      post_types: ["page", "post"],
      layouts: Array.from({ length: 21 }, (_, index) => ({
        name: index === 0 ? "podstrona" : `layout_${index}`,
        label: index === 0 ? "Podstrona" : `Layout ${index}`,
        fields: [],
        source_method: "acf_export",
        required_field_names: [],
        optional_field_names: ["tytul", "glowny_opis"]
      })),
      source_method: "acf_export",
      layouts_discovered: true
    },
    dev_content: {
      status: "available",
      source_method: "acf_rest",
      source_ref: "WORDPRESS_EKOLOGUS_URL wp-json/wp/v2/pages?context=edit",
      page_count: 1,
      pages: [
        {
          post_id: "2",
          slug: "bdo",
          title: "BDO dla firm",
          link: "https://ekologus.dev.proudsite.pl/bdo/",
          status: "publish",
          modified: "2026-07-08T10:00:00",
          modified_gmt: "2026-07-08T08:00:00",
          template: "",
          parent: "",
          acf_field_name: "sekcje_strony",
          section_count: 4,
          sections: [
            {
              section_index: 1,
              acf_field_name: "sekcje_strony",
              layout_name: "baner_startowy",
              layout_label: "Baner startowy",
              title: "BDO dla firm",
              text_summary: "Strona dev ma hero opisujące obowiązki BDO dla firm.",
              field_names: ["modul_naglowka", "przyciski"],
              text_field_paths: ["modul_naglowka.naglowek_modulu"]
            },
            {
              section_index: 2,
              acf_field_name: "sekcje_strony",
              layout_name: "lista_korzysci",
              layout_label: "Lista korzyści",
              title: "Kogo dotyczy BDO",
              text_summary: "Sekcja do dopracowania pod zapytania z GSC.",
              field_names: ["wiersze", "opis_glowny"],
              text_field_paths: ["wiersze.row_1.tytul_wiersza"]
            }
          ]
        }
      ],
      blockers: []
    },
    wp_cli: {
      method: "wp_cli",
      status: "configured",
      configured: true,
      missing_env: [],
      source_refs: ["WORDPRESS_EKOLOGUS_WP_CLI_PATH"]
    },
    helper_plugin: {
      method: "helper",
      status: "not_configured",
      configured: false,
      missing_env: ["WORDPRESS_EKOLOGUS_HELPER_URL"],
      source_refs: []
    },
    write_boundary: {
      allowed_operation: "create_wordpress_draft",
      direct_vendor_write_allowed: false,
      draft_writes_enabled_by_env: false,
      live_write_enabled: false,
      publish_allowed: false,
      destructive_update_allowed: false,
      external_write_attempted: false,
      required_action_contract: "actionobject_validate_preview_review_confirm_audit"
    },
    discovery_facts: [],
    blockers: [],
    evidence_ids: ["ev_connector_wordpress_ekologus_status"],
    source_connectors: ["wordpress_ekologus"]
  };
}

function operatorSteps(): ContentWorkItemWorkflowSnapshotResponse["operator_steps"] {
  return [
    {
      id: "scope",
      title: "Zakres i cel",
      phase: "complete",
      readiness: "ready",
      status_label: "można planować",
      summary: "Strona i usługa są zidentyfikowane.",
      can_open: true,
      can_submit: false,
      blocker: null,
      safe_next_step: "Sprawdź mapę sekcji."
    },
    {
      id: "section_map",
      title: "Plan sekcji",
      phase: "complete",
      readiness: "ready",
      status_label: "mapa gotowa",
      summary: "Publiczna strona, sygnały i dev są zmapowane.",
      can_open: true,
      can_submit: false,
      blocker: null,
      safe_next_step: "Przejdź do pracy nad szkicem."
    },
    {
      id: "draft",
      title: "Szkic treści",
      phase: "current",
      readiness: "review_required",
      status_label: "wymaga zapisanej wersji",
      summary: "Edytuj szkic i przygotuj wersję do review.",
      can_open: true,
      can_submit: false,
      blocker: {
        code: "missing_revision_bound_draft",
        label: "Brakuje zapisanej wersji szkicu",
        reason: "Review nie jest jeszcze powiązane z dokładną wersją treści."
      },
      safe_next_step: "Przygotuj podgląd, a następnie zapisz niezmienną wersję szkicu."
    },
    {
      id: "review",
      title: "Sprawdzenie treści",
      phase: "pending",
      readiness: "blocked",
      status_label: "zablokowane",
      summary: "Review musi dotyczyć dokładnej wersji szkicu.",
      can_open: false,
      can_submit: false,
      blocker: {
        code: "missing_revision_bound_draft",
        label: "Brakuje wersji do review",
        reason: "Stare zatwierdzenie paczki nie zatwierdza dokładnego tekstu."
      },
      safe_next_step: "Najpierw zapisz wersję szkicu."
    },
    {
      id: "dev_draft",
      title: "Szkic na devie",
      phase: "pending",
      readiness: "blocked",
      status_label: "zablokowane",
      summary: "WordPress przyjmuje tylko zaakceptowany szkic draft-only.",
      can_open: false,
      can_submit: false,
      blocker: {
        code: "missing_revision_acceptance",
        label: "Brakuje akceptacji wersji",
        reason: "Nie ma eksperckiej akceptacji dokładnej wersji i śladu audytowego."
      },
      safe_next_step: "Zakończ review konkretnej wersji szkicu."
    }
  ];
}
