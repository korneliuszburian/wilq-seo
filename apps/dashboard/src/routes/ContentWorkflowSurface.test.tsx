import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  applyAction,
  confirmAction,
  getAction,
  getContentWorkItemEnrichment,
  getContentWorkItemQueue,
  getContentWorkItemPlanningProposal,
  getContentWorkItemSemanticReview,
  getContentWorkItemSnapshot,
  getContentWordPressDraftActivationPacket,
  getContentWordPressDraftWriteReadiness,
  getContentWordPressExistingDraftUpdateReadiness,
  getWordPressAuthoringProfile,
  impactCheckAction,
  postContentWorkItemCodexSectionProposal,
  postContentWorkItemInitialDraft,
  postContentWorkItemPlanningProposal,
  postContentWorkItemSemanticReview,
  postContentWorkItemWordPressAuthoringPayloadPreview,
  postContentWorkItemWordPressDraftExecution,
  previewAction,
  reviewAction,
  saveContentWorkItemDraftRevision,
  saveContentWorkItemDraftRevisionReview,
  saveContentWorkItemPlanningReview,
  saveContentWorkItemSnapshotAudit,
  saveContentWorkItemSnapshotHumanReview,
  validateAction,
  type ActionApplyResult,
  type ActionObject,
  type ContentCodexSectionProposalResponse,
  type ContentDraftRevisionBinding,
  type ContentInitialDraftResponse,
  type ContentOpportunityEnrichmentResponse,
  type ContentPlanningProposalResponse,
  type ContentSemanticReviewResponse,
  type ContentWorkItemQueueResponse,
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
import { ContentCodexSectionProposalResult } from "./ContentCodexSectionProposalResult";

vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return {
    ...actual,
    applyAction: vi.fn(),
    confirmAction: vi.fn(),
    getAction: vi.fn(),
    getContentWorkItemEnrichment: vi.fn(),
    getContentWorkItemQueue: vi.fn(),
    getContentWorkItemPlanningProposal: vi.fn(),
    getContentWorkItemSemanticReview: vi.fn(),
    getContentWorkItemSnapshot: vi.fn(),
    getContentWordPressDraftActivationPacket: vi.fn(),
    getContentWordPressDraftWriteReadiness: vi.fn(),
    getContentWordPressExistingDraftUpdateReadiness: vi.fn(),
    getWordPressAuthoringProfile: vi.fn(),
    impactCheckAction: vi.fn(),
    postContentWorkItemCodexSectionProposal: vi.fn(),
    postContentWorkItemInitialDraft: vi.fn(),
    postContentWorkItemPlanningProposal: vi.fn(),
    postContentWorkItemSemanticReview: vi.fn(),
    postContentWorkItemWordPressAuthoringPayloadPreview: vi.fn(),
    postContentWorkItemWordPressDraftExecution: vi.fn(),
    previewAction: vi.fn(),
    reviewAction: vi.fn(),
    saveContentWorkItemDraftRevision: vi.fn(),
    saveContentWorkItemDraftRevisionReview: vi.fn(),
    saveContentWorkItemPlanningReview: vi.fn(),
    saveContentWorkItemSnapshotHumanReview: vi.fn(),
    saveContentWorkItemSnapshotAudit: vi.fn(),
    validateAction: vi.fn()
  };
});

describe("ContentWorkflowSurface", () => {
  beforeEach(() => {
    vi.mocked(getContentWorkItemEnrichment).mockResolvedValue(contentOpportunityEnrichmentResponse());
    vi.mocked(getContentWorkItemQueue).mockResolvedValue(contentQueueResponse());
    vi.mocked(getContentWorkItemPlanningProposal).mockResolvedValue(
      planningProposalStatus()
    );
    vi.mocked(getContentWorkItemSemanticReview).mockResolvedValue(
      semanticReviewNotGenerated()
    );
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
    vi.mocked(saveContentWorkItemSnapshotHumanReview).mockResolvedValue(
      workflowSnapshot({ review: humanReview() }).human_review
    );
    vi.mocked(saveContentWorkItemSnapshotAudit).mockResolvedValue(
      workflowSnapshot({ review: humanReview(), handoff: wordpressHandoff() }).wordpress_handoff
    );
    vi.mocked(postContentWorkItemCodexSectionProposal).mockResolvedValue(
      codexSectionProposalResponse()
    );
    vi.mocked(postContentWorkItemInitialDraft).mockResolvedValue(initialDraftResponse());
    vi.mocked(postContentWorkItemPlanningProposal).mockResolvedValue(
      planningProposalStatus({ status: "created" })
    );
    vi.mocked(postContentWorkItemSemanticReview).mockResolvedValue(
      semanticReviewCreated()
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
    const planning = planningWorkspace();
    vi.mocked(saveContentWorkItemPlanningReview).mockResolvedValue({
      status: "recorded",
      decision: planning.scope_decision!,
      planning_workspace: planning
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
    expect(screen.getByText("Zatwierdź plan sekcji")).toBeInTheDocument();
    expect(await screen.findByText("Źródła użyte")).toBeInTheDocument();
    expect(screen.getByText("3 z 10")).toBeInTheDocument();
    expect(screen.getByText("Powiązanie landing")).toBeInTheDocument();
    expect(screen.getByText("GSC: użyte")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Kogo dotyczy BDO" })).toBeInTheDocument();
    expect(screen.queryByText("Sygnały i braki")).not.toBeInTheDocument();
    expect(screen.queryByText("Tekst sekcji do szkicu")).not.toBeInTheDocument();
    expect(within(taskMap).getByRole("button", { name: /Szkic treści/ })).toHaveAttribute(
      "aria-current",
      "step"
    );
    expect(within(taskMap).getByText(/Oglądasz ukończony krok/)).toBeInTheDocument();

    expect(saveContentWorkItemSnapshotHumanReview).not.toHaveBeenCalled();
    expect(saveContentWorkItemSnapshotAudit).not.toHaveBeenCalled();
    expect(postContentWorkItemWordPressDraftExecution).not.toHaveBeenCalled();
    expect(saveContentWorkItemDraftRevision).not.toHaveBeenCalled();
    expect(saveContentWorkItemDraftRevisionReview).not.toHaveBeenCalled();
    expect(saveContentWorkItemPlanningReview).not.toHaveBeenCalled();
  });

  it("does not present an old proposal as ready when planning input is blocked", async () => {
    const blockedSummary = planningInputSummary();
    blockedSummary.source_assessments = blockedSummary.source_assessments.map((assessment) =>
      assessment.source === "ga4"
        ? {
            ...assessment,
            status: "blocked" as const,
            reason: "GA4 nie ma jeszcze exact landing matchu.",
            evidence_ids: ["ev_ga4_unbound"]
          }
        : assessment
    );
    vi.mocked(getContentWorkItemPlanningProposal).mockResolvedValue(
      planningProposalStatus({
        status: "blocked",
        input_summary: blockedSummary,
        proposal: planningWorkspace({ generated: true }).proposal,
        blockers: [{
          code: "blocked_planning_sources",
          label: "Źródło wymaga dokładnego powiązania",
          reason: "GA4 nie ma jeszcze exact landing matchu.",
          next_step: "Dodaj typed landing match.",
          source_codes: ["ga4"]
        }]
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

    const taskMap = await screen.findByTestId("content-workflow-task-map");
    fireEvent.click(within(taskMap).getByRole("button", { name: /Plan sekcji/ }));

    expect(await screen.findByText("Plan jest zablokowany")).toBeInTheDocument();
    expect(screen.queryByText("Plan strony jest gotowy do review")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Wygeneruj/ })).not.toBeInTheDocument();
    expect(screen.getByText("GA4: zablokowane")).toBeInTheDocument();
  });

  it("uses the loaded snapshot candidate in the task context", async () => {
    const queue = contentQueueResponse();
    queue.candidates[0] = {
      ...queue.candidates[0],
      reason: "Kompaktowa kolejka pokazuje niepełne metryki."
    };
    const snapshot = workflowSnapshot();
    snapshot.candidate = {
      ...snapshot.candidate,
      reason: "Dokładny snapshot pokazuje pełne metryki strony."
    };
    vi.mocked(getContentWorkItemQueue).mockResolvedValue(queue);
    vi.mocked(getContentWorkItemSnapshot).mockResolvedValue(snapshot);

    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow", defaultPendingMinMs: 0 })}
        client={createWilqQueryClient({ defaultOptions: { queries: { retry: false } } })}
      />
    );

    const context = await screen.findByRole("region", {
      name: "Kontekst zadania treściowego"
    });
    expect(within(context).getByText("Dokładny snapshot pokazuje pełne metryki strony.")).toBeTruthy();
    expect(within(context).queryByText("Kompaktowa kolejka pokazuje niepełne metryki.")).toBeNull();
  });

  it("lets the marketer switch the exact evidenced page before the workflow", async () => {
    const appRouter = createWilqRouter({
      initialPath:
        `/content-workflow?work_item_id=content_work_item_bdo&section_heading=Kogo%20dotyczy%20BDO&planning_digest=${"a".repeat(64)}`,
      defaultPendingMinMs: 0
    });
    render(
      <App
        appRouter={appRouter}
        client={createWilqQueryClient({ defaultOptions: { queries: { retry: false } } })}
      />
    );

    const picker = await screen.findByRole("combobox", { name: "Strona i temat" });
    expect(within(picker).getAllByRole("option")).toHaveLength(2);
    expect(picker).toHaveValue("content_work_item_bdo");

    fireEvent.change(picker, { target: { value: "content_work_item_green_deal" } });

    await waitFor(() =>
      expect(getContentWorkItemSnapshot).toHaveBeenCalledWith("content_work_item_green_deal")
    );
    expect(Reflect.get(appRouter.state.location.search, "work_item_id")).toBe(
      "content_work_item_green_deal"
    );
    expect(Reflect.get(appRouter.state.location.search, "section_heading")).toBeUndefined();
    expect(Reflect.get(appRouter.state.location.search, "planning_digest")).toBeUndefined();
    expect(saveContentWorkItemPlanningReview).not.toHaveBeenCalled();
    expect(saveContentWorkItemDraftRevision).not.toHaveBeenCalled();
    expect(postContentWorkItemWordPressDraftExecution).not.toHaveBeenCalled();
  });

  it("falls back to an evidenced queue item for an unknown deep link", async () => {
    render(
      <App
        appRouter={createWilqRouter({
          initialPath: "/content-workflow?work_item_id=missing_work_item",
          defaultPendingMinMs: 0
        })}
        client={createWilqQueryClient({ defaultOptions: { queries: { retry: false } } })}
      />
    );

    const picker = await screen.findByRole("combobox", { name: "Strona i temat" });
    expect(picker).toHaveValue("content_work_item_bdo");
    expect(getContentWorkItemSnapshot).toHaveBeenCalledWith("content_work_item_bdo");
    expect(getContentWorkItemSnapshot).not.toHaveBeenCalledWith("missing_work_item");
  });

  it("follows browser history after the route is already mounted", async () => {
    const appRouter = createWilqRouter({
      initialPath: "/content-workflow?work_item_id=content_work_item_bdo",
      defaultPendingMinMs: 0
    });
    render(
      <App
        appRouter={appRouter}
        client={createWilqQueryClient({ defaultOptions: { queries: { retry: false } } })}
      />
    );

    const picker = await screen.findByRole("combobox", { name: "Strona i temat" });
    expect(picker).toHaveValue("content_work_item_bdo");

    fireEvent.change(picker, { target: { value: "content_work_item_green_deal" } });
    await waitFor(() =>
      expect(screen.getByRole("combobox", { name: "Strona i temat" })).toHaveValue(
        "content_work_item_green_deal"
      )
    );
    await act(async () => {
      appRouter.history.back();
    });

    expect(Reflect.get(appRouter.state.location.search, "work_item_id")).toBe(
      "content_work_item_bdo"
    );
    await waitFor(() =>
      expect(screen.getByRole("combobox", { name: "Strona i temat" })).toHaveValue(
        "content_work_item_bdo"
      )
    );
  });

  it("keeps the session focus on an exact section from the current plan", async () => {
    const appRouter = createWilqRouter({
      initialPath:
        "/content-workflow?work_item_id=content_work_item_bdo&section_heading=Jak%20przygotowa%C4%87%20dokumenty&planning_digest=stale_plan",
      defaultPendingMinMs: 0
    });
    render(
      <App
        appRouter={appRouter}
        client={createWilqQueryClient({ defaultOptions: { queries: { retry: false } } })}
      />
    );

    const sectionPicker = await screen.findByRole("combobox", { name: "Sekcja do pracy" });
    expect(sectionPicker).toHaveValue("Kogo dotyczy BDO");

    fireEvent.change(sectionPicker, { target: { value: "Jak przygotować dokumenty" } });

    await waitFor(() =>
      expect(Reflect.get(appRouter.state.location.search, "section_heading")).toBe(
        "Jak przygotować dokumenty"
      )
    );
    expect(Reflect.get(appRouter.state.location.search, "planning_digest")).toBe("a".repeat(64));
    expect(screen.getByText("Fokus: Jak przygotować dokumenty", { exact: false })).toBeTruthy();
    expect(saveContentWorkItemPlanningReview).not.toHaveBeenCalled();
    expect(saveContentWorkItemDraftRevision).not.toHaveBeenCalled();
  });

  it("starts dynamic planning only from the explicit strategy action", async () => {
    vi.mocked(getContentWorkItemSnapshot).mockResolvedValue(
      workflowSnapshot({
        planning: planningWorkspace({ scopeCurrent: false, sectionMapCurrent: false }),
        workspace: { ...revisionWorkspace(), can_save: false },
        currentStepId: "scope",
        steps: operatorStepsAtScope()
      })
    );
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow", defaultPendingMinMs: 0 })}
        client={createWilqQueryClient({ defaultOptions: { queries: { retry: false } } })}
      />
    );

    fireEvent.click(await screen.findByRole("button", { name: "Wygeneruj plan" }));
    await waitFor(() =>
      expect(postContentWorkItemPlanningProposal).toHaveBeenCalledWith(
        {
          service_card_id: "ekologus_service_bdo_reporting",
          expected_planning_input_digest: "f".repeat(64),
          operator_hint: "",
          requested_by: "wilku"
        },
        "content_work_item_bdo"
      )
    );
    expect(postContentWorkItemWordPressDraftExecution).not.toHaveBeenCalled();
  });

  it("generates one exact full draft and renders a page-like preview", async () => {
    const planning = planningWorkspace({ generated: true });
    const revision = savedFullDraftRevision();
    vi.mocked(postContentWorkItemInitialDraft).mockResolvedValue(
      initialDraftResponse(revision)
    );
    vi.mocked(getContentWorkItemSnapshot)
      .mockResolvedValueOnce(
        workflowSnapshot({ planning, workspace: revisionWorkspace() })
      )
      .mockResolvedValue(
        workflowSnapshot({ planning, workspace: savedRevisionWorkspace(revision) })
      );
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow", defaultPendingMinMs: 0 })}
        client={createWilqQueryClient({ defaultOptions: { queries: { retry: false } } })}
      />
    );

    fireEvent.click(await screen.findByRole("button", { name: "Wygeneruj pełny tekst" }));
    await waitFor(() =>
      expect(postContentWorkItemInitialDraft).toHaveBeenCalledWith(
        {
          expected_proposal_id: "content_planning_proposal_bdo",
          expected_planning_digest: "a".repeat(64),
          expected_planning_input_digest: "f".repeat(64),
          requested_by: "wilku"
        },
        "content_work_item_bdo"
      )
    );
    const preview = await screen.findByTestId("content-full-page-preview");
    expect(within(preview).getByRole("heading", { name: "BDO bez chaosu w dokumentach" }))
      .toBeInTheDocument();
    expect(within(preview).getByText("Najpierw sprawdź sytuację swojej firmy."))
      .toBeInTheDocument();
    expect(within(preview).getByText("Jak zacząć sprawdzanie BDO?"))
      .toBeInTheDocument();
    expect(within(preview).getByText("Opisz sytuację firmy i poproś o weryfikację."))
      .toBeInTheDocument();
    expect(postContentWorkItemWordPressDraftExecution).not.toHaveBeenCalled();
  });

  it("records scope review and resumes on the section map without a wall of panels", async () => {
    const initialPlanning = planningWorkspace({ scopeCurrent: false, sectionMapCurrent: false });
    const reviewedPlanning = planningWorkspace({ scopeCurrent: true, sectionMapCurrent: false });
    vi.mocked(getContentWorkItemSnapshot)
      .mockResolvedValueOnce(
        workflowSnapshot({
          planning: initialPlanning,
          workspace: { ...revisionWorkspace(), can_save: false },
          currentStepId: "scope",
          steps: operatorStepsAtScope()
        })
      )
      .mockResolvedValue(
        workflowSnapshot({
          planning: reviewedPlanning,
          workspace: { ...revisionWorkspace(), can_save: false },
          currentStepId: "section_map",
          steps: operatorStepsAtSectionMap()
        })
      );
    vi.mocked(saveContentWorkItemPlanningReview).mockResolvedValue({
      status: "recorded",
      decision: reviewedPlanning.scope_decision!,
      planning_workspace: reviewedPlanning
    });
    const client = createWilqQueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    expect(await screen.findByText("Zatwierdź zakres treści")).toBeInTheDocument();
    expect(screen.getByText("właściciel firmy")).toBeInTheDocument();
    expect(screen.getByText("Skontaktuj się z Ekologus.")).toBeInTheDocument();
    expect(screen.getByText("bdo odpady")).toBeInTheDocument();
    expect(screen.getByText(/120 wyśw. · 12 klik. · CTR 10.0%/)).toBeInTheDocument();
    expect(screen.getByText(/brak ścisłego mapowania do strony i usługi/)).toBeInTheDocument();
    fireEvent.click(
      screen.getByLabelText("Sprawdziłem stronę, usługę, intencję, odbiorcę i CTA.")
    );
    fireEvent.click(screen.getByRole("button", { name: "Zapisz decyzję i przejdź dalej" }));

    await waitFor(() => expect(saveContentWorkItemPlanningReview).toHaveBeenCalledTimes(1));
    expect(saveContentWorkItemPlanningReview).toHaveBeenCalledWith(
      {
        stage: "scope",
        expected_planning_digest: initialPlanning.proposal.planning_digest,
        service_card_id: "service_bdo",
        decision: "approved",
        reviewed_by: "wilku",
        checked_items: ["zakres i CTA"],
        notes: ""
      },
      "content_work_item_bdo"
    );
    expect(await screen.findByText("Zatwierdź plan sekcji")).toBeInTheDocument();
    expect(screen.queryByText("Aktualna strona")).not.toBeInTheDocument();
    expect(postContentWorkItemWordPressDraftExecution).not.toHaveBeenCalled();
  });

  it("keeps the planning note after a stale conflict and offers an explicit refresh", async () => {
    const planning = planningWorkspace({ scopeCurrent: false, sectionMapCurrent: false });
    vi.mocked(getContentWorkItemSnapshot).mockResolvedValue(
      workflowSnapshot({
        planning,
        workspace: { ...revisionWorkspace(), can_save: false },
        currentStepId: "scope",
        steps: operatorStepsAtScope()
      })
    );
    vi.mocked(saveContentWorkItemPlanningReview).mockResolvedValue({
      detail: "Plan treści zmienił się. Odśwież element przed zapisaniem decyzji."
    });
    const client = createWilqQueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    await screen.findByText("Zatwierdź zakres treści");
    fireEvent.change(screen.getByLabelText("Decyzja planistyczna"), {
      target: { value: "needs_changes" }
    });
    const note = "CTA powinno prowadzić do formularza dla usługi BDO.";
    fireEvent.change(screen.getByLabelText("Notatka do planu"), {
      target: { value: note }
    });
    fireEvent.click(screen.getByRole("button", { name: "Zapisz uwagi do poprawy" }));

    expect(await screen.findByText("Plan zmienił się na serwerze")).toBeInTheDocument();
    expect(screen.getByLabelText("Notatka do planu")).toHaveValue(note);
    fireEvent.click(screen.getByRole("button", { name: "Odśwież aktualny plan" }));
    await waitFor(() => expect(getContentWorkItemSnapshot).toHaveBeenCalledTimes(2));
    expect(postContentWorkItemWordPressDraftExecution).not.toHaveBeenCalled();
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
    fireEvent.click(screen.getByRole("button", { name: "Zapisz poprawioną wersję do review" }));

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
    fireEvent.click(screen.getByRole("button", { name: "Zapisz poprawioną wersję do review" }));

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
    expect(screen.queryByRole("button", { name: "Zapisz poprawioną wersję do review" }))
      .not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Wygeneruj pełny tekst" })).toBeDisabled();
    expect(screen.queryByRole("button", { name: "Sprawdź tekst szkicu" })).not.toBeInTheDocument();
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

  it("shows persisted advisory findings without approving or writing the revision", async () => {
    const revision = savedFullDraftRevision();
    vi.mocked(getContentWorkItemSnapshot).mockResolvedValue(
      workflowSnapshot({
        workspace: savedRevisionWorkspace(revision),
        currentStepId: "review",
        steps: operatorStepsAtReview()
      })
    );
    vi.mocked(getContentWorkItemSemanticReview).mockResolvedValue(
      semanticReviewNotGenerated(revision)
    );
    vi.mocked(postContentWorkItemSemanticReview).mockResolvedValue(
      semanticReviewCreated(revision)
    );
    const client = createWilqQueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } }
    });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    expect(await screen.findByText("Advisory review semantyczne")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Uruchom review semantyczne" }));

    await waitFor(() =>
      expect(postContentWorkItemSemanticReview).toHaveBeenCalledWith(
        {
          expected_revision_digest: revision.content_digest,
          requested_by: "wilku"
        },
        revision.work_item_id,
        revision.revision_id
      )
    );
    const result = await screen.findByTestId("semantic-review-result");
    expect(within(result).getByText("1 konkretnych uwag do decyzji")).toBeInTheDocument();
    expect(within(result).getByText("Odpowiedź zaczyna się zbyt ogólnie"))
      .toBeInTheDocument();
    expect(within(result).getByText("Przenieś konkretną odpowiedź na początek sekcji."))
      .toBeInTheDocument();
    expect(saveContentWorkItemDraftRevisionReview).not.toHaveBeenCalled();

    const childRevision = {
      ...revision,
      revision_id: "content_revision_bdo_full_2",
      revision_number: 2,
      base_revision_id: revision.revision_id,
      content_digest: "b".repeat(64),
      created_at: "2026-07-16T18:05:00Z"
    };
    const decision = savedDraftRevisionReview(revision, "needs_changes");
    vi.mocked(saveContentWorkItemDraftRevisionReview).mockResolvedValue({
      status: "recorded",
      review: decision,
      workspace: needsChangesRevisionWorkspace(revision)
    });
    vi.mocked(getContentWorkItemSnapshot).mockResolvedValue(
      workflowSnapshot({
        workspace: savedRevisionWorkspace(childRevision),
        currentStepId: "review",
        steps: operatorStepsAtReview()
      })
    );
    vi.mocked(getContentWorkItemSemanticReview).mockResolvedValue(
      {
        ...semanticReviewCreated(revision),
        status: "stale",
        safe_next_step: "Wersja zmieniła się; uruchom nowe review."
      }
    );
    fireEvent.change(screen.getByLabelText("Notatka do decyzji"), {
      target: { value: "Popraw bezpośredniość wskazanej sekcji." }
    });
    fireEvent.click(screen.getByRole("button", { name: "Zapisz decyzję dla wersji 1" }));

    await waitFor(() => expect(getContentWorkItemSnapshot).toHaveBeenCalledTimes(2));
    await waitFor(() =>
      expect(screen.queryByText("Odpowiedź zaczyna się zbyt ogólnie")).not.toBeInTheDocument()
    );
    expect(postContentWorkItemWordPressDraftExecution).not.toHaveBeenCalled();
    expect(postContentWorkItemWordPressAuthoringPayloadPreview).not.toHaveBeenCalled();
  });

  it("runs the exact revision ActionObject inline and stops a typed apply blocker without retry", async () => {
    const revision = savedDraftRevision();
    const revisionReview = savedDraftRevisionReview(revision);
    const binding = draftRevisionBinding(revision, revisionReview);
    const handoff = {
      ...wordpressHandoff(),
      revision_binding: binding,
      revision_sections: revision.sections
    };
    vi.mocked(getContentWorkItemSnapshot).mockResolvedValue(
      workflowSnapshot({
        review: humanReview(),
        handoff,
        workspace: approvedRevisionWorkspace(revision, revisionReview),
        currentStepId: "dev_draft",
        steps: operatorStepsAtDevDraft()
      })
    );

    let actionState = wordpressDraftAction();
    let eventSequence = 0;
    const appendEvent = (eventType: string, blockers: unknown[] = []) => {
      eventSequence += 1;
      const event = actionAuditEvent(eventType, binding, eventSequence, blockers);
      actionState = { ...actionState, audit_events: [...actionState.audit_events, event] };
      return event;
    };
    vi.mocked(getAction).mockImplementation(async () => ({
      ...actionState,
      audit_events: [...actionState.audit_events]
    }));
    vi.mocked(validateAction).mockResolvedValue({
      action_id: actionState.id,
      valid: true,
      status: "valid",
      status_label: "Akcja poprawna",
      errors: [],
      warnings: [],
      checked_at: "2026-07-15T10:00:00Z"
    });
    vi.mocked(previewAction).mockImplementation(async () => ({
      action_id: actionState.id,
      status: "preview_ready",
      status_label: "Podgląd gotowy",
      dry_run: true,
      mutation_allowed: false,
      preview_contract: "wordpress_draft_handoff_preview_v1",
      preview_items: [],
      preview_cards: [],
      preview_items_total: 0,
      omitted_items: 0,
      blockers: [],
      blocker_labels: [],
      audit_event: appendEvent("action_preview_generated"),
      review_gate: actionState.review_gate
    }));
    vi.mocked(reviewAction).mockImplementation(async () => ({
      action_id: actionState.id,
      status: "recorded",
      status_label: "Review zapisane",
      audit_event: appendEvent("human_review_approved_for_prepare"),
      review_gate: actionState.review_gate
    }));
    vi.mocked(confirmAction).mockImplementation(async () => ({
      action_id: actionState.id,
      confirmed: true,
      status: "confirmed",
      status_label: "Potwierdzenie zapisane",
      blockers: [],
      blocker_labels: [],
      audit_event: appendEvent("action_apply_confirmed"),
      review_gate: actionState.review_gate
    }));
    vi.mocked(impactCheckAction).mockImplementation(async () => ({
      action_id: actionState.id,
      status: "checked",
      status_label: "Gotowość sprawdzona",
      pre_window_days: 7,
      post_window_days: 7,
      metric_fact_count: 0,
      source_connectors: ["wordpress_ekologus"],
      source_connector_labels: ["WordPress Ekologus"],
      evidence_ids: ["ev_wp_bdo"],
      evidence_summary_label: "1 dowód",
      blockers: [],
      blocker_labels: [],
      audit_event: appendEvent("action_impact_check_completed"),
      review_gate: actionState.review_gate
    }));
    const applyBlocker = {
      code: "wordpress_revision_binding_mismatch",
      label: "Wersja szkicu zmieniła się",
      reason: "Zaakceptowana wersja nie odpowiada już przekazaniu.",
      next_step: "Wróć do review aktualnej wersji."
    };
    vi.mocked(applyAction).mockImplementation(async () => {
      const auditEvent = appendEvent("action_apply_blocked", [applyBlocker]);
      return {
        action_id: actionState.id,
        applied: false,
        status: "blocked",
        status_label: "Zapis zablokowany",
        audit_event: auditEvent,
        mutation_audit: {
          id: "mutation_audit_exact_revision_blocked",
          action_id: actionState.id,
          connector: "wordpress_ekologus",
          action_type: "wordpress_draft_handoff",
          status: "blocked",
          status_label: "Zapis zablokowany",
          adapter_reached: false,
          external_write_attempted: false,
          mutation_attempted: false,
          mutation_adapter: "wordpress_draft_execution_boundary",
          actor: "operator_local_dashboard",
          created_at: "2026-07-15T10:00:06Z",
          audit_event_id: auditEvent.id,
          evidence_ids: ["ev_wp_bdo"],
          blockers: [applyBlocker.code],
          wordpress_draft_binding: binding,
          wordpress_revision_blockers: [applyBlocker],
          summary: "Adapter nie został wywołany.",
          redacted: true
        },
        errors: [applyBlocker.reason],
        wordpress_revision_blockers: [applyBlocker]
      } satisfies ActionApplyResult;
    });

    const client = createWilqQueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } }
    });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    await waitFor(() => expect(getAction).toHaveBeenCalledWith("act_apply_wordpress_draft_handoff"));
    await screen.findByText("Wersja 1 → szkic na devie");
    const wizard = screen.getByTestId("content-wordpress-draft-action-wizard");
    expect(within(wizard).getByText("Wersja 1 → szkic na devie")).toBeInTheDocument();
    expect(within(wizard).getByText(/bez publikacji · bez aktualizacji/)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /kanoniczną akcję/ })).not.toBeInTheDocument();
    expect(within(wizard).queryByRole("button", { name: "Utwórz szkic na devie" }))
      .not.toBeInTheDocument();

    fireEvent.click(within(wizard).getByRole("button", { name: "Sprawdź wersję i podgląd" }));
    await waitFor(() => expect(previewAction).toHaveBeenCalledTimes(1));
    expect(validateAction).toHaveBeenCalledTimes(1);
    expect(previewAction).toHaveBeenCalledWith(
      "act_apply_wordpress_draft_handoff",
      expect.objectContaining({ wordpress_draft: binding })
    );

    const reviewCheckbox = await within(wizard).findByRole("checkbox", {
      name: /Sprawdziłem podgląd tej wersji/
    });
    expect(within(wizard).getByRole("button", { name: "Zapisz review akcji" })).toBeDisabled();
    fireEvent.click(reviewCheckbox);
    fireEvent.click(within(wizard).getByRole("button", { name: "Zapisz review akcji" }));
    await waitFor(() => expect(reviewAction).toHaveBeenCalledTimes(1));
    expect(reviewAction).toHaveBeenCalledWith(
      "act_apply_wordpress_draft_handoff",
      expect.objectContaining({ wordpress_draft: binding })
    );

    const confirmCheckbox = await within(wizard).findByRole("checkbox", {
      name: /Potwierdzam zamiar utworzenia wyłącznie draftu/
    });
    expect(within(wizard).getByRole("button", { name: "Potwierdź draft-only" })).toBeDisabled();
    fireEvent.click(confirmCheckbox);
    fireEvent.click(within(wizard).getByRole("button", { name: "Potwierdź draft-only" }));
    await waitFor(() => expect(confirmAction).toHaveBeenCalledTimes(1));
    expect(confirmAction).toHaveBeenCalledWith(
      "act_apply_wordpress_draft_handoff",
      expect.objectContaining({ wordpress_draft: binding })
    );

    fireEvent.click(await within(wizard).findByRole("button", { name: "Sprawdź gotowość zapisu" }));
    await waitFor(() => expect(impactCheckAction).toHaveBeenCalledTimes(1));
    expect(impactCheckAction).toHaveBeenCalledWith(
      "act_apply_wordpress_draft_handoff",
      expect.objectContaining({ wordpress_draft: binding })
    );

    fireEvent.click(await within(wizard).findByRole("button", { name: "Utwórz szkic na devie" }));
    await waitFor(() => expect(applyAction).toHaveBeenCalledTimes(1));
    expect(applyAction).toHaveBeenCalledWith("act_apply_wordpress_draft_handoff", {
      confirm: true,
      confirmed_by: "operator_local_dashboard",
      wordpress_draft: binding
    });
    expect(await within(wizard).findByText("Wersja szkicu zmieniła się")).toBeInTheDocument();
    expect(within(wizard).getByText(/Wróć do review aktualnej wersji/)).toBeInTheDocument();
    expect(within(wizard).getByRole("button", { name: "Utwórz szkic na devie" })).toBeDisabled();
    expect(applyAction).toHaveBeenCalledTimes(1);
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
    expect(postContentWorkItemWordPressDraftExecution).not.toHaveBeenCalled();
  });

  it("sends a human-selected advisory section by stable ID", async () => {
    const revision = savedFullDraftRevision();
    vi.mocked(getContentWorkItemSnapshot).mockResolvedValue(
      workflowSnapshot({ workspace: needsChangesRevisionWorkspace(revision) })
    );
    vi.mocked(getContentWorkItemSemanticReview).mockResolvedValue(
      semanticReviewCreated(revision).review
        ? { ...semanticReviewCreated(revision), status: "ready" }
        : semanticReviewNotGenerated(revision)
    );
    vi.mocked(postContentWorkItemCodexSectionProposal).mockImplementation(
      () => new Promise(() => undefined)
    );
    const client = createWilqQueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } }
    });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    expect(await screen.findByText("Wskazane w advisory review")).toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("checkbox", { name: /Kogo dotyczy BDO/ })
    );
    fireEvent.click(screen.getByRole("button", { name: "Popraw 1 sekcję z Codexem" }));

    await waitFor(() =>
      expect(postContentWorkItemCodexSectionProposal).toHaveBeenCalledWith(
        {
          expected_base_digest: revision.content_digest,
          selected_section_headings: [],
          selected_section_ids: [revision.sections[0]?.section_id],
          requested_by: "wilku"
        },
        revision.work_item_id,
        revision.revision_id
      )
    );
    expect(saveContentWorkItemDraftRevisionReview).not.toHaveBeenCalled();
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
    expect(postContentWorkItemWordPressDraftExecution).not.toHaveBeenCalled();
  });

  it("lets Wilku revise one reviewed section and keeps the Codex child draft-only", async () => {
    const revision = savedDraftRevision();
    vi.mocked(getContentWorkItemSnapshot).mockResolvedValue(
      workflowSnapshot({ workspace: needsChangesRevisionWorkspace(revision) })
    );
    let resolveProposal:
      | ((response: ContentCodexSectionProposalResponse) => void)
      | undefined;
    vi.mocked(postContentWorkItemCodexSectionProposal).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveProposal = resolve;
        })
    );
    const client = createWilqQueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } }
    });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    expect(await screen.findByText("Popraw wersję 1 z Codexem")).toBeInTheDocument();
    expect(screen.getByText(/Uwagi z review: „Ta wersja wymaga opisanych poprawek/))
      .toBeInTheDocument();
    const proposalButton = screen.getByRole("button", {
      name: "Popraw 0 sekcji z Codexem"
    });
    expect(proposalButton).toBeDisabled();

    fireEvent.click(screen.getByRole("checkbox", { name: "Kogo dotyczy BDO" }));
    expect(proposalButton).toBeEnabled();
    fireEvent.click(proposalButton);

    await waitFor(() =>
      expect(postContentWorkItemCodexSectionProposal).toHaveBeenCalledWith(
        {
          expected_base_digest: revision.content_digest,
          selected_section_headings: ["Kogo dotyczy BDO"],
          selected_section_ids: [],
          requested_by: "wilku"
        },
        revision.work_item_id,
        revision.revision_id
      )
    );
    expect(screen.getByRole("status")).toHaveTextContent(
      "Codex poprawia 1 sekcję i sprawdza przypisane dowody"
    );

    resolveProposal?.(codexSectionProposalResponse());
    const result = await screen.findByTestId("codex-proposal-result");
    expect(result).toHaveTextContent("Wersja 2 utworzona · wymaga review człowieka");
    expect(result).toHaveTextContent("Zapisana treść pierwszej wersji o obowiązkach BDO.");
    expect(result).toHaveTextContent(
      "Sprawdź, czy zakres działalności firmy tworzy obowiązki BDO"
    );
    expect(result).toHaveTextContent("Wzmocnij CTA");
    expect(result).toHaveTextContent("Semantyka nadal wymaga sprawdzenia człowieka");
    expect(result).toHaveTextContent("Szkic nie jest gotowy do publikacji");
    expect(screen.getByText(/Run Codex: codex_section_run_bdo_1/)).not.toBeVisible();
    expect(screen.queryByRole("button", { name: "Sprawdź gotowość szkicu" }))
      .not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Przygotuj podgląd draftu" }))
      .not.toBeInTheDocument();
    expect(postContentWorkItemWordPressDraftExecution).not.toHaveBeenCalled();
    expect(postContentWorkItemWordPressAuthoringPayloadPreview).not.toHaveBeenCalled();

    await openWorkflowDetails();
    fireEvent.click(screen.getByRole("button", { name: /Zielony Ład dla firm/ }));
    await waitFor(() =>
      expect(getContentWorkItemSnapshot).toHaveBeenCalledWith("content_work_item_green_deal")
    );
    expect(screen.queryByTestId("codex-proposal-result")).not.toBeInTheDocument();
  });

  it("fails closed when the Codex child omits a selected section", () => {
    const baseRevision = savedDraftRevision();
    const response = codexSectionProposalResponse();
    if (!response.revision) throw new Error("Expected a created proposal fixture");

    render(
      <ContentCodexSectionProposalResult
        expectedWorkItemId={baseRevision.work_item_id}
        baseRevision={baseRevision}
        result={{ ...response, revision: { ...response.revision, sections: [] } }}
        onRefresh={vi.fn()}
      />
    );

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Nie można potwierdzić porównania wersji"
    );
    expect(screen.queryByTestId("codex-proposal-result")).not.toBeInTheDocument();
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
    await screen.findByRole("button", { name: "Przygotuj mapowanie sekcji ACF" });
    fireEvent.click(screen.getByRole("button", { name: "Przygotuj mapowanie sekcji ACF" }));

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
    expect(screen.getAllByText("Główny opis (glowny_opis)").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Lead (lead)").length).toBeGreaterThan(0);
    expect(postContentWorkItemWordPressDraftExecution).not.toHaveBeenCalled();
  });

  it("disables technical WordPress dry-runs when API readiness is blocked", async () => {
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

    await openWorkflowDetails();
    expect(screen.getByRole("button", { name: "Sprawdź podgląd draftu" })).toBeDisabled();
    expect(
      screen.getByRole("button", { name: "Sprawdź payload WordPress bez zapisu" })
    ).toBeDisabled();
    expect(screen.queryByRole("button", { name: "Przygotuj podgląd draftu" }))
      .not.toBeInTheDocument();
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
      screen.getByRole("button", {
        name: "Sprawdź payload WordPress bez zapisu"
      })
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
  await screen.findByTestId("content-workflow-technical-audit");
}

function planningProposalStatus(
  overrides: Partial<ContentPlanningProposalResponse> = {}
): ContentPlanningProposalResponse {
  return {
    status: "not_generated",
    work_item_id: "content_work_item_bdo",
    service_card_id: "ekologus_service_bdo_reporting",
    planning_input_digest: "f".repeat(64),
    input_summary: planningInputSummary(),
    proposal: null,
    runtime: {
      status: "not_started",
      thread_id: null,
      turn_id: null,
      event_methods: [],
      item_types: [],
      external_call_attempted: false
    },
    blockers: [],
    safe_next_step: "Wygeneruj pierwszy plan i sprawdź go przed decyzją człowieka.",
    publish_ready: false,
    ...overrides
  };
}

function planningInputSummary(): NonNullable<ContentPlanningProposalResponse["input_summary"]> {
  return {
    final_canonical_url: "https://www.ekologus.pl/bdo/",
    service_label: "BDO i sprawozdawczość środowiskowa",
    inventory_status: "available",
    source_assessments: [
      {
        source: "wordpress",
        status: "used",
        reason: "Publiczne inventory jest aktualne.",
        landing_match_tiers: ["host_alias"],
        evidence_ids: ["ev_wp_bdo"],
        knowledge_card_ids: []
      },
      {
        source: "service_profile",
        status: "used",
        reason: "Karta usługi jest zatwierdzona.",
        landing_match_tiers: [],
        evidence_ids: ["ev_service_bdo"],
        knowledge_card_ids: ["ekologus_service_bdo_reporting"]
      },
      {
        source: "gsc",
        status: "used",
        reason: "Dokładne zapytania GSC są aktualne.",
        landing_match_tiers: ["tracking_only"],
        evidence_ids: [],
        knowledge_card_ids: []
      },
      ...(["ga4", "google_ads", "ahrefs", "keyword_planner", "merchant", "localo", "social"] as const)
        .map((source) => ({
          source,
          status: "not_applicable" as const,
          reason: "To źródło nie zasila tego planu.",
          landing_match_tiers: [],
          evidence_ids: [],
          knowledge_card_ids: []
        }))
    ],
    source_fact_count: 2,
    evidence_id_count: 3,
    knowledge_card_count: 1,
    measurement_metrics: ["gsc_clicks"]
  };
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
    wordpress_content_inventory_status: "available",
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
  planning = planningWorkspace(),
  currentStepId = "draft",
  steps = operatorSteps()
}: {
  review?: ReturnType<typeof humanReview> | null;
  handoff?: ReturnType<typeof wordpressHandoff> | null;
  workspace?: ContentWorkItemWorkflowSnapshotResponse["revision_workspace"];
  planning?: ContentWorkItemWorkflowSnapshotResponse["planning_workspace"];
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
    structured_generation_readiness: {
      status: "ready",
      editable_section_headings: ["Kogo dotyczy BDO"],
      blockers: [],
      safe_next_step: "Wybierz sekcje zapisanej wersji do poprawy z Codexem.",
      publish_ready: false
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
      review_recordable: Boolean(review),
      review_recorded: Boolean(review),
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
    planning_workspace: planning,
    current_step_id: currentStepId,
    operator_steps: steps
  };
}

function planningWorkspace({
  scopeCurrent = true,
  sectionMapCurrent = true,
  generated = false
}: {
  scopeCurrent?: boolean;
  sectionMapCurrent?: boolean;
  generated?: boolean;
} = {}): NonNullable<ContentWorkItemWorkflowSnapshotResponse["planning_workspace"]> {
  const proposal = {
    work_item_id: "content_work_item_bdo",
    planning_digest: "a".repeat(64),
    proposal_id: generated ? "content_planning_proposal_bdo" : null,
    proposal_version: generated ? 1 : null,
    codex_run_id: generated ? "codex_content_planning_bdo" : null,
    generation_status: generated ? "codex_generated" as const : "baseline" as const,
    planning_input_digest: generated ? "f".repeat(64) : null,
    input_schema_version: "wilq_content_planning_input_v1",
    criteria_version: "wilq_people_first_planning_v1",
    final_canonical_url: "https://ekologus.pl/bdo/",
    service_card_id: "service_bdo",
    service_label: "BDO i sprawozdawczość środowiskowa",
    service_selection_confirmed: true,
    human_override_review_required: false,
    target_reader: "właściciel firmy",
    buyer_problem: "Firma nie wie, które obowiązki BDO jej dotyczą.",
    buyer_trigger: "Zbliża się termin sprawozdania.",
    search_intent: "sprawdzenie obowiązków i wybór wsparcia",
    angle: "Odpowiedz bezpośrednio na pytania firmy.",
    value_proposition: "Wyjaśnij zakres wsparcia na podstawie dowodów.",
    cta_direction: "Skontaktuj się z Ekologus.",
    internal_link_directions: ["Kontakt", "Oferta BDO"],
    sections: draftPackage().sections.map((section) => ({
      section_id: `section_${section.heading.toLowerCase().replaceAll(" ", "_")}`,
      heading: section.heading,
      purpose: section.purpose,
      reader_question: section.purpose,
      inventory_disposition: "rewrite" as const,
      query_terms: [],
      claim_ids: [],
      evidence_ids: section.evidence_ids
    })),
    search_demand: {
      status: "available" as const,
      gsc_query_rows: [{
        source_kind: "gsc_query" as const,
        source_connector: "google_search_console" as const,
        term: "bdo odpady",
        page: "https://ekologus.pl/bdo/",
        landing_match_tiers: ["host_alias" as const],
        service_card_id: "service_bdo",
        alignment_basis: "gsc_exact_page" as const,
        review_required: false,
        section_headings: ["Kogo dotyczy BDO"],
        section_mapping_status: "intent_relevance" as const,
        period: "last_28_days",
        freshness: "fresh" as const,
        collected_at: "2026-07-15T12:00:00Z",
        evidence_ids: ["ev_gsc_bdo"],
        impressions: 120,
        clicks: 12,
        ctr: 0.1,
        average_position: 6.4,
        average_monthly_searches: null,
        cost_micros: null,
        conversions: null,
        conversion_value: null
      }],
      ads_term_rows: [],
      keyword_planner_rows: [],
      source_connectors: ["google_search_console"],
      evidence_ids: ["ev_gsc_bdo"],
      optional_ads_status: "not_exactly_mapped" as const,
      optional_ads_evidence_ids: [],
      optional_ads_blockers: [],
      safe_next_step: "Sprawdź zapytania GSC przypisane do strony i sekcji."
    },
    page_assets: {
      title: "BDO dla firm",
      h1: "BDO dla firm",
      lead: "Sprawdź obowiązki BDO swojej firmy.",
      meta_title: "BDO dla firm — Ekologus",
      meta_description: "Sprawdź obowiązki BDO swojej firmy."
    },
    faq: [],
    cta_blocks: [],
    internal_links: [],
    conditional_hypotheses: [],
    measurement_plan: {
      metrics_to_watch: ["gsc_clicks"],
      baseline_evidence_ids: ["ev_gsc_bdo"],
      observation_rule: "Porównaj równoważne okresy po publikacji.",
      success_claim_rule: "Nie claimuj efektu bez obserwacji."
    },
    evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
    source_connectors: ["google_search_console", "wordpress_ekologus"]
  };
  const decision = (stage: "scope" | "section_map") => ({
    decision_id: `planning_${stage}`,
    decision_number: 1,
    work_item_id: proposal.work_item_id,
    stage,
    planning_digest: proposal.planning_digest,
    service_card_id: proposal.service_card_id,
    human_override_review_required: false,
    decision: "approved" as const,
    reviewed_by: "wilku",
    checked_items: [stage === "scope" ? "zakres i CTA" : "kolejność, cel i dowody"],
    notes: "Sprawdzono plan.",
    created_at: "2026-07-16T00:00:00Z"
  });
  return {
    proposal,
    scope_decision: scopeCurrent ? decision("scope") : null,
    section_map_decision: sectionMapCurrent ? decision("section_map") : null,
    scope_current: scopeCurrent,
    section_map_current: sectionMapCurrent
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
      query_terms: [],
      evidence_ids: [...section.evidence_ids],
      claim_ids: []
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
    schema_version: "wilq_content_draft_revision_v1",
    revision_id: "content_revision_bdo_1",
    work_item_id: "content_work_item_bdo",
    revision_number: 1,
    base_revision_id: null,
    content_digest: "a".repeat(64),
    draft_package_id: "draft_package_content_work_item_bdo",
    draft_package_digest: "d".repeat(64),
    planning_digest: "a".repeat(64),
    final_canonical_url: "https://ekologus.pl/bdo/",
    title: workspace.editor_title,
    sections: workspace.editor_sections.map((section, index) => ({
      ...section,
      body_markdown:
        index === 0 ? "Zapisana treść pierwszej wersji o obowiązkach BDO." : section.body_markdown
    })),
    faq: [],
    cta_blocks: [],
    internal_links: [],
    publish_ready: false,
    created_by: "wilku",
    created_at: "2026-07-14T04:00:00Z"
  };
}

function savedFullDraftRevision(): NonNullable<
  ContentWorkItemWorkflowSnapshotResponse["revision_workspace"]["latest_revision"]
> {
  const legacy = savedDraftRevision();
  return {
    ...legacy,
    schema_version: "wilq_content_draft_revision_v2",
    revision_id: "content_revision_bdo_full_1",
    planning_input_digest: "f".repeat(64),
    service_card_id: "ekologus_service_bdo_reporting",
    service_digest: "e".repeat(64),
    inventory_digest: "1".repeat(64),
    title: "Pełny tekst BDO dla firm",
    page_assets: {
      wordpress_title: "Pełny tekst BDO dla firm",
      meta_title: "BDO dla firm — Ekologus",
      meta_description: "Sprawdź sytuację firmy i dokumenty.",
      h1: "BDO bez chaosu w dokumentach",
      lead: "Najpierw sprawdź sytuację swojej firmy."
    },
    sections: legacy.sections.map((section, index) => ({
      ...section,
      section_id: `section_bdo_${index + 1}`,
      query_terms: index === 0 ? ["bdo odpady"] : [],
      claim_ids: [],
      body_markdown: `Pełna odpowiedź sekcji ${index + 1} oparta na planie i dowodach.`
    })),
    faq: [{
      faq_id: "faq_bdo_start",
      question: "Jak zacząć sprawdzanie BDO?",
      answer_markdown: "Zacznij od sytuacji firmy i rodzaju prowadzonej działalności.",
      query_terms: ["bdo odpady"],
      evidence_ids: ["ev_gsc_bdo"],
      claim_ids: []
    }],
    cta_blocks: [{
      cta_id: "cta_bdo_contact",
      placement: "after_content",
      body_markdown: "Opisz sytuację firmy i poproś o weryfikację.",
      evidence_ids: ["ev_wp_bdo"],
      claim_ids: []
    }],
    internal_links: [],
    proposal_metadata: {
      source: "codex_app_server",
      codex_run_id: "codex_content_initial_draft_bdo",
      selected_section_headings: legacy.sections.map((section) => section.heading),
      section_lineage: legacy.sections.map((section) => ({
        heading: section.heading,
        evidence_ids: section.evidence_ids,
        claim_ids: []
      })),
      quality_verdict: "ready_for_human_review",
      quality_finding_codes: ["semantic_review_required"],
      review_scope: "persisted_full_document_and_declared_lineage",
      semantic_review_required: true
    }
  };
}

function initialDraftResponse(
  revision = savedFullDraftRevision()
): ContentInitialDraftResponse {
  return {
    status: "created",
    work_item_id: revision.work_item_id,
    proposal_id: "content_planning_proposal_bdo",
    run_id: "codex_content_initial_draft_bdo",
    revision,
    runtime: {
      status: "completed",
      thread_id: "thread_initial_bdo",
      turn_id: "turn_initial_bdo",
      event_methods: ["turn/completed"],
      item_types: ["agentMessage"],
      external_call_attempted: false
    },
    blockers: [],
    safe_next_step: "Przeczytaj pełną stronę i zapisz decyzję człowieka.",
    publish_ready: false
  };
}

function semanticReviewNotGenerated(
  revision = savedFullDraftRevision()
): ContentSemanticReviewResponse {
  return {
    status: "not_generated",
    work_item_id: revision.work_item_id,
    revision_id: revision.revision_id,
    revision_digest: revision.content_digest,
    review: null,
    run_id: null,
    runtime: {
      status: "not_started",
      thread_id: null,
      turn_id: null,
      event_methods: [],
      item_types: [],
      external_call_attempted: false
    },
    blockers: [],
    safe_next_step: "Uruchom advisory review.",
    publish_ready: false,
    human_review_required: true,
    action_object_created: false
  };
}

function semanticReviewCreated(
  revision = savedFullDraftRevision()
): ContentSemanticReviewResponse {
  const sectionId = revision.sections[0]?.section_id ?? "section_bdo_1";
  const dimensions = [
    "answer_directness",
    "completeness",
    "logical_flow",
    "specificity",
    "repetition",
    "search_intent_fit",
    "buyer_fit",
    "credibility",
    "conversion_clarity"
  ] as const;
  const review = {
    review_id: "content_semantic_review_bdo_1",
    work_item_id: revision.work_item_id,
    revision_id: revision.revision_id,
    revision_digest: revision.content_digest,
    criteria_version: "wilq_semantic_content_review_v1" as const,
    codex_run_id: "codex_content_semantic_review_bdo_1",
    status: "needs_changes" as const,
    dimensions: dimensions.map((dimension) => ({
      dimension,
      status: dimension === "answer_directness" ? "needs_changes" as const : "strong" as const,
      reason: "Ocena dokładnej wersji dokumentu.",
      affected_targets: [sectionId]
    })),
    findings: [{
      finding_id: "content_semantic_review_bdo_1_finding_01",
      dimension: "answer_directness" as const,
      severity: "medium" as const,
      label: "Odpowiedź zaczyna się zbyt ogólnie",
      reason: "Czytelnik zbyt późno widzi decyzję.",
      instruction: "Przenieś konkretną odpowiedź na początek sekcji.",
      affected_targets: [sectionId],
      evidence_ids: ["ev_gsc_bdo"]
    }],
    evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
    source_connectors: ["google_search_console", "wordpress_ekologus"],
    requested_by: "wilku",
    created_at: "2026-07-16T18:00:00Z",
    safe_next_step: "Wybierz sekcje do poprawy.",
    publish_ready: false as const,
    human_review_required: true as const,
    action_object_created: false as const
  };
  return {
    status: "created",
    work_item_id: revision.work_item_id,
    revision_id: revision.revision_id,
    revision_digest: revision.content_digest,
    review,
    run_id: review.codex_run_id,
    runtime: {
      status: "completed",
      thread_id: "thread_semantic_bdo",
      turn_id: "turn_semantic_bdo",
      event_methods: ["turn/completed"],
      item_types: ["agentMessage"],
      external_call_attempted: false
    },
    blockers: [],
    safe_next_step: review.safe_next_step,
    publish_ready: false,
    human_review_required: true,
    action_object_created: false
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

function approvedRevisionWorkspace(
  revision: ReturnType<typeof savedDraftRevision>,
  review: ReturnType<typeof savedDraftRevisionReview>
): ContentWorkItemWorkflowSnapshotResponse["revision_workspace"] {
  return {
    ...savedRevisionWorkspace(revision),
    status: "approved",
    latest_review: review,
    can_save: false,
    can_review: false,
    safe_next_step: "Przekaż dokładną wersję do WordPress jako nowy szkic."
  };
}

function draftRevisionBinding(
  revision: ReturnType<typeof savedDraftRevision>,
  review: ReturnType<typeof savedDraftRevisionReview>
): ContentDraftRevisionBinding {
  return {
    work_item_id: revision.work_item_id,
    handoff_id: "wordpress_draft_handoff_content_work_item_bdo",
    revision_id: revision.revision_id,
    content_digest: revision.content_digest,
    draft_package_id: revision.draft_package_id,
    draft_package_digest: revision.draft_package_digest,
    planning_digest: revision.planning_digest!,
    approval_decision_id: review.decision_id,
    final_canonical_url: revision.final_canonical_url
  };
}

function operatorStepsAtDevDraft(): ContentWorkItemWorkflowSnapshotResponse["operator_steps"] {
  return operatorSteps().map((step) => ({
    ...step,
    phase: step.id === "dev_draft" ? "current" : "complete",
    readiness: "ready",
    status_label: step.id === "dev_draft" ? "gotowe do bezpiecznego przekazania" : "gotowe",
    can_open: true,
    can_submit: step.id === "dev_draft",
    blocker: null,
    safe_next_step:
      step.id === "dev_draft"
        ? "Przejdź przez podgląd, review, potwierdzenie i kontrolę zapisu."
        : step.safe_next_step
  }));
}

function wordpressDraftAction(): ActionObject {
  return {
    id: "act_apply_wordpress_draft_handoff",
    title: "Utwórz szkic WordPress",
    domain: "wordpress",
    connector: "wordpress_ekologus",
    connector_label: "WordPress Ekologus",
    mode: "apply",
    mode_label: "zapis",
    risk: "high",
    risk_label: "wysokie",
    status: "ready",
    status_label: "gotowe do review",
    evidence_ids: ["ev_wp_bdo"],
    evidence_summary_label: "1 dowód",
    metrics: [],
    human_diagnosis: "Dokładna wersja wymaga kontrolowanego handoffu.",
    recommended_reason: "Utwórz wyłącznie nowy szkic.",
    validation_status: "valid",
    validation_status_label: "poprawna",
    review_gate: {
      status: "validated_prepare_only",
      status_label: "wymaga review",
      summary: "Zapis wymaga pełnego śladu.",
      required_checks: [],
      required_check_labels: [],
      operator_checklist: [],
      operator_checklist_labels: [],
      apply_blockers: [],
      apply_blocker_labels: [],
      apply_blocker_summary_label: "",
      confirmation_required: true,
      apply_allowed: false,
      last_mutation_blockers: [],
      last_mutation_blocker_labels: [],
      last_mutation_blocker_summary_label: ""
    },
    preview_cards: [],
    payload: {
      action_type: "wordpress_draft_handoff",
      allowed_operation: "create_wordpress_draft"
    },
    audit_events: []
  };
}

function actionAuditEvent(
  eventType: string,
  binding: ContentDraftRevisionBinding,
  sequence: number,
  wordpressRevisionBlockers: unknown[] = []
): ActionObject["audit_events"][number] {
  return {
    id: `audit_exact_revision_${sequence}`,
    action_id: "act_apply_wordpress_draft_handoff",
    event_type: eventType,
    event_type_label: eventType,
    actor: "operator_local_dashboard",
    created_at: `2026-07-15T10:00:0${sequence}Z`,
    summary: eventType,
    evidence_ids: ["ev_wp_bdo"],
    details: {
      wordpress_draft_binding: binding,
      wordpress_revision_blockers: wordpressRevisionBlockers
    },
    redacted: true
  };
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
    service_selection_confirmed: true,
    human_override_review_required: false,
    service_candidates: [
      {
        service_card_id: "ekologus_service_bdo_reporting",
        service_label: "BDO i sprawozdawczość środowiskowa",
        lifecycle_status: "source_backed_review_required" as const,
        lifecycle_label: "źródło wymaga review",
        matched_terms: ["bdo"],
        match_reasons: ["Temat lub adres strony zawiera dokładną frazę „bdo”."],
        recommended: true
      }
    ],
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

function wordpressHandoff(): NonNullable<
  ContentWorkItemWorkflowSnapshotResponse["wordpress_handoff"]["handoff_result"]["handoff"]
> {
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
    revision_sections: [],
    publish_allowed: false,
    destructive_update_allowed: false
  };
}

function codexSectionProposalResponse(): ContentCodexSectionProposalResponse {
  const base = savedDraftRevision();
  const heading = base.sections[0]?.heading ?? "Kogo dotyczy BDO";
  const runId = "codex_section_run_bdo_1";
  const child = {
    ...base,
    revision_id: "content_revision_bdo_2",
    revision_number: 2,
    base_revision_id: base.revision_id,
    content_digest: "b".repeat(64),
    sections: base.sections.map((section, index) =>
      index === 0
        ? {
            ...section,
            body_markdown:
              "Sprawdź, czy zakres działalności firmy tworzy obowiązki BDO, a następnie umów konsultację z Ekologus na podstawie dokumentów firmy."
          }
        : section
    ),
    proposal_metadata: {
      source: "codex_app_server" as const,
      codex_run_id: runId,
      selected_section_headings: [heading],
      section_lineage: [
        {
          heading,
          evidence_ids: ["ev_gsc_bdo"],
          claim_ids: ["claim_general_bdo"]
        }
      ],
      quality_verdict: "needs_changes" as const,
      quality_finding_codes: ["weak_cta"],
      review_scope: "persisted_selected_sections_and_declared_lineage" as const,
      semantic_review_required: true as const
    },
    created_by: "codex_app_server",
    created_at: "2026-07-15T18:00:00Z"
  };
  const dimension = (label: string, status: "pass" | "needs_changes" = "pass") => ({
    status,
    label,
    reason: status === "pass" ? "WILQ nie wykrył problemu." : "Ten obszar wymaga poprawy."
  });

  return {
    status: "created",
    run_id: runId,
    work_item_id: base.work_item_id,
    base_revision_id: base.revision_id,
    selected_section_headings: [heading],
    revision: child,
    quality_review: {
      review_id: "quality_review_content_revision_bdo_2",
      work_item_id: base.work_item_id,
      draft_package_id: base.draft_package_id,
      verdict: "needs_changes",
      evidence_coverage: dimension("Pokrycie dowodami"),
      claim_safety: dimension("Bezpieczeństwo twierdzeń"),
      duplicate_risk: dimension("Ryzyko duplikacji"),
      usefulness: dimension("Użyteczność", "needs_changes"),
      service_fit: dimension("Dopasowanie do usługi"),
      search_intent_fit: dimension("Dopasowanie do intencji"),
      buyer_problem_fit: dimension("Problem kupującego"),
      cta_quality: dimension("Jakość CTA", "needs_changes"),
      factual_precision: dimension("Precyzja faktów"),
      polish_language_quality: dimension("Język polski"),
      internal_link_fit: dimension("Linkowanie wewnętrzne"),
      measurement_readiness: dimension("Gotowość pomiaru"),
      blockers: [],
      findings: [
        {
          code: "weak_cta",
          severity: "needs_changes",
          label: "Wzmocnij CTA",
          reason: "Wezwanie do kontaktu nadal wymaga wskazania konkretnego następnego kroku.",
          next_step: "Doprecyzuj zakres konsultacji.",
          affected_section: heading,
          evidence_ids: ["ev_gsc_bdo"],
          source_connectors: ["google_search_console"]
        }
      ],
      revision_instructions: [],
      evidence_ids: ["ev_gsc_bdo"],
      source_connectors: ["google_search_console"],
      safe_next_step: "Przeczytaj child revision i wykonaj review człowieka."
    },
    quality_review_scope: "persisted_selected_sections_and_declared_lineage",
    semantic_review_required: true,
    runtime: {
      status: "completed",
      thread_id: "thread_bdo_1",
      turn_id: "turn_bdo_1",
      event_methods: ["thread/started", "turn/completed"],
      item_types: ["agent_message"],
      external_call_attempted: false
    },
    evidence_ids: ["ev_gsc_bdo"],
    source_connectors: ["google_search_console"],
    blockers: [],
    safe_next_step: "Przejdź do review dokładnej wersji 2.",
    publish_ready: false
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
        meta_write_status: "not_present",
        metadata_blockers: [],
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

function operatorStepsAtScope(): ContentWorkItemWorkflowSnapshotResponse["operator_steps"] {
  return operatorSteps().map((step, index) => ({
    ...step,
    phase: index === 0 ? "current" : "pending",
    readiness: index === 0 ? "review_required" : "blocked",
    can_open: index === 0,
    can_submit: index === 0,
    blocker:
      index === 0
        ? {
            code: "scope_review_missing",
            label: "Zakres wymaga decyzji marketera",
            reason: "Zakres nie został jeszcze zatwierdzony."
          }
        : step.blocker
  }));
}

function operatorStepsAtSectionMap(): ContentWorkItemWorkflowSnapshotResponse["operator_steps"] {
  return operatorSteps().map((step, index) => ({
    ...step,
    phase: index === 0 ? "complete" : index === 1 ? "current" : "pending",
    readiness: index === 0 ? "ready" : index === 1 ? "review_required" : "blocked",
    can_open: index <= 1,
    can_submit: index === 1,
    blocker:
      index === 1
        ? {
            code: "section_map_review_missing",
            label: "Plan sekcji wymaga decyzji marketera",
            reason: "Plan sekcji nie został jeszcze zatwierdzony."
          }
        : index === 0
          ? null
          : step.blocker
  }));
}
