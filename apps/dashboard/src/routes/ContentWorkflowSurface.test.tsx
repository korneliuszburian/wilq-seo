import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  applyAction,
  confirmAction,
  getAction,
  getConnectorRefreshRun,
  getContentWorkItemEnrichment,
  getContentWorkItemInitialDraft,
  getContentWorkItemEditorialIntegrity,
  getContentWorkItemRevisionHtmlPackage,
  getContentWorkItemDecisionContext,
  getContentWorkItemDocumentWorkspace,
  getContentInventoryCatalog,
  getContentOperatorContext,
  getContentServiceProfile,
  getContentWorkItemQueue,
  getKnowledgeSourceMaterialReadiness,
  getKnowledgeSourceMaterials,
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
  refreshConnector,
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
  type ContentDecisionContext,
  type ContentDocumentWorkspace,
  type ContentInventoryCatalogResponse,
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
import { ContentDecisionContextPanel } from "./ContentDecisionContextPanel";
import { summarizeGa4MetricFacts } from "./ContentWorkflowJourneyContext";
import { workflowStepActionLabel, workflowStepInstruction } from "./ContentWorkflowSurface";

describe("workflowStepActionLabel", () => {
  it("does not imply dev readiness when the current handoff step is blocked", () => {
    expect(workflowStepActionLabel("dev_draft", true)).toBe("Sprawdź blokadę dev preview");
    expect(workflowStepActionLabel("review", true)).toBe("Sprawdź blokadę review");
  });

  it("keeps normal current-step actions when no blocker exists", () => {
    expect(workflowStepActionLabel("dev_draft", false)).toBe("Otwórz dev preview");
    expect(workflowStepActionLabel("scope", true)).toBe("Otwórz formularz zakresu");
  });

  it("puts the API blocker reason into the marketer-facing instruction", () => {
    expect(workflowStepInstruction("review", { label: "Review wymaga decyzji", reason: "Brak decyzji dla exact revision." })).toBe(
      "Review wymaga decyzji: Brak decyzji dla exact revision."
    );
    expect(workflowStepInstruction("review")).toContain("Uruchom advisory review");
  });
});

vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return {
    ...actual,
    applyAction: vi.fn(),
    confirmAction: vi.fn(),
    getAction: vi.fn(),
    getConnectorRefreshRun: vi.fn(),
    getContentWorkItemEnrichment: vi.fn(),
    getContentWorkItemInitialDraft: vi.fn(),
    getContentWorkItemEditorialIntegrity: vi.fn(),
    getContentWorkItemRevisionHtmlPackage: vi.fn(),
    getContentWorkItemDecisionContext: vi.fn(),
    getContentWorkItemDocumentWorkspace: vi.fn(),
    getContentInventoryCatalog: vi.fn(),
    getContentOperatorContext: vi.fn(),
    getContentServiceProfile: vi.fn(),
    getContentWorkItemQueue: vi.fn(),
    getKnowledgeSourceMaterialReadiness: vi.fn(),
    getKnowledgeSourceMaterials: vi.fn(),
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
    refreshConnector: vi.fn(),
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
    vi.mocked(getContentOperatorContext).mockResolvedValue({
      display_label: "Wilku (lokalny pilot)",
      request_label: "wilku",
      principal_id: "local_operator",
      trust_level: "local_unverified",
      authentication_status: "not_configured"
    } as never);
    vi.mocked(getContentWorkItemEnrichment).mockResolvedValue(contentOpportunityEnrichmentResponse());
    vi.mocked(getContentWorkItemInitialDraft).mockResolvedValue(initialDraftResponse());
    vi.mocked(getContentWorkItemDecisionContext).mockResolvedValue(contentDecisionContext());
    vi.mocked(getContentWorkItemDocumentWorkspace).mockResolvedValue(contentDocumentWorkspace());
    vi.mocked(getContentInventoryCatalog).mockResolvedValue(contentInventoryCatalog());
    vi.mocked(getContentServiceProfile).mockResolvedValue(serviceProfileContext() as never);
    vi.mocked(getContentWorkItemQueue).mockResolvedValue(contentQueueResponse());
    vi.mocked(getKnowledgeSourceMaterialReadiness).mockResolvedValue(knowledgeReadiness());
    vi.mocked(getKnowledgeSourceMaterials).mockResolvedValue([]);
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
    vi.unstubAllGlobals();
  });

  it("keeps GA4 metric grouping stable when source rows arrive in another order", () => {
    const facts = workItem().metric_facts ?? [];
    const reordered = [...facts].reverse();
    expect(summarizeGa4MetricFacts(facts)).toEqual(summarizeGa4MetricFacts(reordered));
    const duplicate = { ...facts[0] };
    const unknown = { ...facts[0], name: "new_metric", metric_label: "nowa metryka", value: 7 };
    expect(summarizeGa4MetricFacts([...facts, duplicate, unknown])).toContain(
      "nowa metryka (google / organic: 7)"
    );
    expect(summarizeGa4MetricFacts(facts)).toEqual([
      "aktywni użytkownicy (google / cpc: 12, google / organic: 26)",
      "wskaźnik zaangażowania (google / organic: 42%)"
    ]);
  });

  it("opens an API-owned context with one marketer-first safe action for a blocked public page", async () => {
    const blockedQueue = contentQueueResponse();
    blockedQueue.candidates[0] = {
      ...blockedQueue.candidates[0],
      recommended_mode: "block",
      recommended_mode_label: "wstrzymaj — odśwież źródło",
      status_label: "wymaga aktualnych dowodów",
      reason: "GSC jest nieświeże.",
      freshness_assessment: staleGscFreshnessAssessment(),
      blockers: [{
        code: "stale_connector_google_search_console",
        label: "GSC wymaga odświeżenia",
        reason: "GSC jest nieświeże.",
        next_step: "Odśwież GSC.",
        decision_id: "decision_bdo",
        evidence_ids: ["ev_gsc_bdo"],
        source_connectors: ["google_search_console"]
      }]
    };
    blockedQueue.freshness_assessment = staleGscFreshnessAssessment();
    vi.mocked(getContentWorkItemQueue).mockResolvedValue(blockedQueue);

    const client = createWilqQueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    expect(await screen.findByTestId("content-decision-context")).toBeInTheDocument();
    expect(getContentWorkItemDecisionContext).toHaveBeenCalledWith("content_work_item_bdo");
    expect(screen.getByText("Target dev niepotwierdzony")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Odśwież GSC" })).toBeInTheDocument();
    expect(screen.getByText("Stan pracy")).toBeInTheDocument();
    expect(screen.getByText("Rekomendacja WILQ")).toBeInTheDocument();
    expect(screen.queryByText("Stan tej decyzji")).not.toBeInTheDocument();
    expect(screen.queryByText("Decyzja", { exact: true })).not.toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Odśwież GSC" })).toHaveLength(1);
    const actionHeading = screen.getByRole("heading", { name: "Odśwież GSC" });
    const publicSourceLabel = screen.getByText("Publiczne źródło");
    expect(actionHeading.compareDocumentPosition(publicSourceLabel) & Node.DOCUMENT_POSITION_FOLLOWING).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING
    );
    expect(screen.getByText(/kontrakt inventory/).closest("details")).not.toBeNull();
    expect(screen.getByText(/evidence-bound/).closest("details")).not.toBeNull();
    expect(screen.getByText(/ActionObject/).closest("details")).not.toBeNull();
    expect(screen.getByText(/accepted revision/).closest("details")).not.toBeNull();
    expect(screen.queryByText("WILQ blokuje pisanie tego tematu")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Sprawdź stronę ponownie" })).not.toBeInTheDocument();
    expect(getContentWorkItemSnapshot).not.toHaveBeenCalled();
    expect(postContentWorkItemInitialDraft).not.toHaveBeenCalled();
    expect(postContentWorkItemWordPressDraftExecution).not.toHaveBeenCalled();
  });

  it("opens the read-only text workspace only after the API-owned open_workspace action", async () => {
    const readyContext = contentDecisionContext();
    readyContext.evidence_readiness = {
      ...readyContext.evidence_readiness,
      status: "ready",
      label: "Dowody są aktualne",
      reason: "Dowody są aktualne dla tej strony.",
      blocker_codes: []
    };
    readyContext.next_safe_action = {
      kind: "open_workspace",
      label: "Otwórz warsztat strony",
      reason: "Możesz przejść do istniejącego warsztatu tej samej strony.",
      connector_id: null
    };
    vi.mocked(getContentWorkItemDecisionContext).mockResolvedValue(readyContext);

    const client = createWilqQueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    expect(await screen.findByTestId("content-decision-context")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Otwórz warsztat strony" })).toBeInTheDocument();
    expect(getContentWorkItemSnapshot).not.toHaveBeenCalled();

    vi.clearAllMocks();
    fireEvent.click(screen.getByRole("button", { name: "Otwórz warsztat strony" }));

    expect(await screen.findByTestId("content-text-workspace")).toBeInTheDocument();
    expect(screen.getByTestId("content-source-snapshot")).toHaveTextContent("Aktualny materiał BDO");
    const canvas = screen.getByTestId("content-workspace-canvas");
    const outline = screen.getByLabelText("Struktura strony");
    expect(canvas.compareDocumentPosition(outline) & Node.DOCUMENT_POSITION_FOLLOWING).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING
    );
    expect(screen.getAllByText("Jak prowadzić ewidencję odpadów?")).toHaveLength(2);
    fireEvent.click(screen.getByRole("button", { name: "Nowa wersja" }));
    expect(screen.getByText("Nowa wersja czeka na review")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Porównanie" }));
    expect(screen.getByText("Brak bezpośrednio rozpoznanego odpowiednika.")).toBeInTheDocument();
    expect(getContentWorkItemDocumentWorkspace).toHaveBeenCalledWith("content_work_item_bdo");
    expect(getContentWorkItemQueue).not.toHaveBeenCalled();
    expect(getContentInventoryCatalog).not.toHaveBeenCalled();
    expect(getContentServiceProfile).not.toHaveBeenCalled();
    expect(getKnowledgeSourceMaterialReadiness).not.toHaveBeenCalled();
    expect(getKnowledgeSourceMaterials).not.toHaveBeenCalled();
    expect(getContentOperatorContext).not.toHaveBeenCalled();
    expect(getContentWorkItemSnapshot).not.toHaveBeenCalled();
    expect(postContentWorkItemInitialDraft).not.toHaveBeenCalled();
    expect(postContentWorkItemWordPressDraftExecution).not.toHaveBeenCalled();
    expect(previewAction).not.toHaveBeenCalled();
  });

  it("does not claim that a document exists when the workspace has no revision", async () => {
    const noDocument = contentDocumentWorkspace();
    noDocument.canonical_document = {
      status: "not_created",
      revision_id: null,
      content_digest: null,
      review_state: "unreviewed",
      label: "Nowa wersja nie została jeszcze przygotowana",
      reason: "Nie ma jeszcze zapisanej wersji dokumentu.",
      preview: null
    };
    noDocument.comparison = {
      status: "unavailable",
      reason: "Porównanie pojawi się po zapisaniu nowej wersji dokumentu.",
      items: []
    };
    noDocument.next_action = {
      kind: "prepare_document",
      label: "Przygotuj nową wersję",
      reason: "Przygotowanie dokumentu jest kolejnym krokiem."
    };
    vi.mocked(getContentWorkItemDocumentWorkspace).mockResolvedValue(noDocument);

    const client = createWilqQueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo&text=%221%22", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    expect(await screen.findByTestId("content-text-workspace")).toBeInTheDocument();
    expect(screen.getByText(/stan nowego dokumentu i dostępne porównanie/)).toBeInTheDocument();
    expect(screen.queryByText(/przygotowany dokument i uczciwe różnice/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Nowa wersja" }));
    expect(screen.getAllByText("Nowa wersja nie została jeszcze przygotowana")).toHaveLength(3);
  });

  it("records human review for the exact Text revision without opening a content write path", async () => {
    const readyContext = contentDecisionContext();
    readyContext.evidence_readiness = {
      ...readyContext.evidence_readiness,
      status: "ready",
      label: "Dowody są aktualne",
      reason: "Dowody są aktualne dla tej strony.",
      blocker_codes: []
    };
    readyContext.next_safe_action = {
      kind: "open_workspace",
      label: "Otwórz warsztat strony",
      reason: "Możesz przejść do read-only warsztatu tej samej strony.",
      connector_id: null
    };
    const revision = savedFullDraftRevision();
    const workspace = {
      ...savedRevisionWorkspace(revision as never),
      latest_revision: revision,
      editor_title: revision.title,
      editor_sections: revision.sections
    } as ContentWorkItemWorkflowSnapshotResponse["revision_workspace"];
    vi.mocked(getContentWorkItemDecisionContext).mockResolvedValue(readyContext);
    vi.mocked(getContentWorkItemInitialDraft).mockResolvedValue(initialDraftResponse(revision));
    vi.mocked(getContentWorkItemSnapshot).mockResolvedValue(workflowSnapshot({ workspace }));

    const client = createWilqQueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo&text=%221%22&review=%221%22", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    expect(await screen.findByTestId("content-review-workspace")).toBeInTheDocument();
    expect(screen.getByTestId("content-full-page-preview")).toBeInTheDocument();
    const save = screen.getByRole("button", { name: "Zapisz review" });
    expect(save).toBeDisabled();
    fireEvent.click(screen.getByRole("checkbox", { name: "Przeczytano dokładną treść tej wersji." }));
    fireEvent.click(screen.getByRole("checkbox", { name: "Sprawdzono dowody przypisane do tej wersji." }));
    expect(save).toBeEnabled();
    fireEvent.click(save);

    await waitFor(() => expect(saveContentWorkItemDraftRevisionReview).toHaveBeenCalledTimes(1));
    expect(vi.mocked(saveContentWorkItemDraftRevisionReview).mock.calls[0]).toEqual([
      expect.objectContaining({
        expected_revision_digest: revision.content_digest,
        reviewed_by: "wilku",
        decision: "approved",
        checked_items: [
          "Przeczytano dokładną treść tej wersji.",
          "Sprawdzono dowody przypisane do tej wersji."
        ],
        evidence_ids: uniqueTestEvidence(revision)
      }),
      revision.work_item_id,
      revision.revision_id
    ]);
    expect(postContentWorkItemInitialDraft).not.toHaveBeenCalled();
    expect(postContentWorkItemWordPressDraftExecution).not.toHaveBeenCalled();
  });

  it("downloads only the exact approved revision as a read-only HTML package", async () => {
    const readyContext = contentDecisionContext();
    readyContext.evidence_readiness = {
      ...readyContext.evidence_readiness,
      status: "ready",
      label: "Dowody są aktualne",
      reason: "Dowody są aktualne dla tej strony.",
      blocker_codes: []
    };
    readyContext.next_safe_action = {
      kind: "open_workspace",
      label: "Otwórz warsztat strony",
      reason: "Możesz przejść do read-only warsztatu tej samej strony.",
      connector_id: null
    };
    const revision = savedFullDraftRevision();
    const review = savedDraftRevisionReview(revision, "approved");
    const workspace = {
      ...savedRevisionWorkspace(revision as never),
      latest_revision: revision,
      latest_review: review,
      status: "approved",
      can_review: false,
      editor_title: revision.title,
      editor_sections: revision.sections
    } as ContentWorkItemWorkflowSnapshotResponse["revision_workspace"];
    vi.mocked(getContentWorkItemDecisionContext).mockResolvedValue(readyContext);
    vi.mocked(getContentWorkItemInitialDraft).mockResolvedValue(initialDraftResponse(revision));
    vi.mocked(getContentWorkItemSnapshot).mockResolvedValue(workflowSnapshot({ workspace }));
    vi.mocked(getContentWorkItemRevisionHtmlPackage).mockResolvedValue({
      manifest: {
        work_item_id: revision.work_item_id,
        revision_id: revision.revision_id,
        content_digest: revision.content_digest,
        final_canonical_url: revision.final_canonical_url,
        evidence_ids: uniqueTestEvidence(revision),
        source_material_ids: revision.source_material_ids,
        knowledge_card_ids: revision.knowledge_card_ids,
        section_count: revision.sections.length
      },
      file_name: `wilq-exact-revision-${revision.revision_id}.html`,
      html_document: "<!doctype html><html><body>Dokument</body></html>"
    });
    const createObjectURL = vi.fn(() => "blob:approved-revision");
    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", { createObjectURL, revokeObjectURL });
    const anchorClick = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);

    const client = createWilqQueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo&text=%221%22&review=%221%22", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    expect(await screen.findByTestId("content-approved-html-package")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Pobierz paczkę HTML" }));

    await waitFor(() => expect(getContentWorkItemRevisionHtmlPackage).toHaveBeenCalledWith(revision.work_item_id, revision.revision_id));
    expect(createObjectURL).toHaveBeenCalledTimes(1);
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:approved-revision");
    expect(postContentWorkItemInitialDraft).not.toHaveBeenCalled();
    expect(postContentWorkItemWordPressDraftExecution).not.toHaveBeenCalled();
    anchorClick.mockRestore();
  });

  it("reads editorial integrity for the exact revision without starting a revision or review mutation", async () => {
    const readyContext = contentDecisionContext();
    readyContext.evidence_readiness = { ...readyContext.evidence_readiness, status: "ready", label: "Dowody są aktualne", reason: "Dowody są aktualne dla tej strony.", blocker_codes: [] };
    readyContext.next_safe_action = { kind: "open_workspace", label: "Otwórz warsztat strony", reason: "Możesz przejść do read-only warsztatu tej samej strony.", connector_id: null };
    const revision = { ...savedFullDraftRevision(), base_revision_id: "content_revision_base" };
    vi.mocked(getContentWorkItemDecisionContext).mockResolvedValue(readyContext);
    vi.mocked(getContentWorkItemInitialDraft).mockResolvedValue(initialDraftResponse(revision));
    vi.mocked(getContentWorkItemEditorialIntegrity).mockResolvedValue({
      work_item_id: revision.work_item_id,
      baseline_revision: { revision_id: "content_revision_r8", content_digest: "b".repeat(64), revision_number: 8 },
      direct_parent_revision: { revision_id: "content_revision_r10", content_digest: "c".repeat(64), revision_number: 10 },
      child_revision: { revision_id: revision.revision_id, content_digest: revision.content_digest, revision_number: 11 },
      human_review: { decision: "approved", reviewed_by: "operator_local_dashboard" },
      observed_scope: { section_ids: revision.sections.map((section) => section.section_id ?? "section"), fields: ["body"] },
      structural_invariants: { section_ids_unchanged: true, section_order_unchanged: true, headings_unchanged: true, title_unchanged: true, faq_unchanged: true, cta_semantics_unchanged: true, links_unchanged: true, evidence_lineage_unchanged: true },
      protected_content_units: [{ unit_id: "unit_r10", section_id: "section_1", section_heading: "Ewidencja odpadów", claim_ids: [], evidence_ids: [], before_excerpt: "Sprawdź rodzaje i ilości odpadów.", after_excerpt: "Ustal rodzaje i ilości odpadów.", status: "changed" }],
      representation_alignment: [{ section_id: "section_1", section_heading: "Ewidencja odpadów", source_body_sha256: "d".repeat(64), rendered_html_sha256: "e".repeat(64), normalized_source_text_sha256: "d".repeat(64), normalized_rendered_text_sha256: "e".repeat(64), status: "aligned" }],
      lint_signals: [{ code: "repeated_root_warto", section_id: null, occurrences: 3, excerpts: [], reason: "Rdzeń „warto” powtarza się 3 razy; raport nie ocenia, czy to błąd stylu." }],
      human_readable_diff: "Niezmienniki struktury naruszone: 0.",
      result: "integrity_ok"
    });
    const client = createWilqQueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<App appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo&text=%221%22", defaultPendingMinMs: 0 })} client={client} />);

    fireEvent.click(await screen.findByRole("button", { name: "Sprawdź zmiany względem wersji bazowej" }));
    await waitFor(() => expect(getContentWorkItemEditorialIntegrity).toHaveBeenCalledWith(revision.work_item_id, revision.revision_id));
    expect(await screen.findByText("Twarda integralność zachowana")).toBeInTheDocument();
    expect(screen.getByText(/Porównanie: R8 → R10 → R11/)).toBeInTheDocument();
    expect(screen.getByText(/Human review tej rewizji: zatwierdzone/)).toBeInTheDocument();
    expect(postContentWorkItemInitialDraft).not.toHaveBeenCalled();
    expect(saveContentWorkItemDraftRevisionReview).not.toHaveBeenCalled();
  });

  it("does not reinterpret inspect_object as opening the text workspace", async () => {
    const inspectContext = contentDecisionContext();
    inspectContext.evidence_readiness = {
      ...inspectContext.evidence_readiness,
      status: "ready",
      label: "Dowody są aktualne",
      reason: "Dowody są aktualne dla tej strony.",
      blocker_codes: []
    };
    inspectContext.next_safe_action = {
      kind: "inspect_object",
      label: "Uzupełnij rozpoznanie obiektu",
      reason: "Brakuje rozpoznania obiektu publicznego.",
      connector_id: null
    };
    vi.mocked(getContentWorkItemDecisionContext).mockResolvedValue(inspectContext);

    const client = createWilqQueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    expect(await screen.findByTestId("content-decision-context")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Otwórz warsztat strony" })).not.toBeInTheDocument();
    expect(screen.queryByTestId("content-text-workspace")).not.toBeInTheDocument();
    expect(getContentWorkItemSnapshot).not.toHaveBeenCalled();
  });

  it("refreshes only the connector named by the context once, then refetches that same context", async () => {
    const blockedQueue = contentQueueResponse();
    blockedQueue.candidates[0] = {
      ...blockedQueue.candidates[0],
      recommended_mode: "block",
      source_public_url: "https://ekologus.pl/bdo/"
    };
    vi.mocked(getContentWorkItemQueue).mockResolvedValue(blockedQueue);
    const refreshedContext = contentDecisionContext();
    refreshedContext.evidence_readiness = {
      ...refreshedContext.evidence_readiness,
      status: "ready",
      label: "Dowody są aktualne",
      reason: "Dowody są aktualne po odczycie GSC.",
      blocker_codes: []
    };
    refreshedContext.next_safe_action = {
      kind: "inspect_object",
      label: "Uzupełnij rozpoznanie obiektu",
      reason: "Brakuje potwierdzonego obiektu WordPress i celu dev.",
      connector_id: null
    };
    vi.mocked(getContentWorkItemDecisionContext)
      .mockResolvedValueOnce(contentDecisionContext())
      .mockResolvedValueOnce(refreshedContext);
    vi.mocked(refreshConnector).mockResolvedValue({
      id: "refresh-gsc-bdo-1",
      connector_id: "google_search_console",
      connector_label: "Google Search Console",
      mode: "vendor_read",
      status: "queued",
      status_label: "odczyt w kolejce",
      started_at: "2026-07-22T10:00:00Z",
      completed_at: null,
      evidence_ids: [],
      evidence_summary_label: "0 dowodów źródłowych",
      missing_credentials: [],
      checked_credentials: [],
      external_call_attempted: false,
      vendor_data_collected: false,
      metrics_persisted: false,
      metric_summary: {},
      summary: "Odczyt GSC został dodany do kolejki.",
      errors: [],
      redacted: true
    });
    vi.mocked(getConnectorRefreshRun).mockResolvedValue({
      id: "refresh-gsc-bdo-1",
      connector_id: "google_search_console",
      connector_label: "Google Search Console",
      mode: "vendor_read",
      status: "completed",
      status_label: "odczyt zakończony",
      started_at: "2026-07-22T10:00:00Z",
      completed_at: "2026-07-22T10:00:01Z",
      evidence_ids: ["ev_refresh_gsc_bdo"],
      evidence_summary_label: "1 dowód źródłowy",
      missing_credentials: [],
      checked_credentials: [],
      external_call_attempted: true,
      vendor_data_collected: true,
      metrics_persisted: true,
      metric_summary: {},
      summary: "Odczyt GSC zakończony.",
      errors: [],
      redacted: true
    });

    const client = createWilqQueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    const refreshButton = await screen.findByRole("button", { name: "Odśwież GSC" });
    fireEvent.click(refreshButton);
    fireEvent.click(refreshButton);

    await waitFor(() => expect(refreshConnector).toHaveBeenCalledTimes(1));
    expect(refreshConnector).toHaveBeenCalledWith("google_search_console", expect.anything());
    await waitFor(() => expect(getConnectorRefreshRun).toHaveBeenCalledWith("refresh-gsc-bdo-1"));
    await waitFor(() => expect(getContentWorkItemDecisionContext).toHaveBeenCalledTimes(2));
    expect(await screen.findByTestId("content-decision-context")).toBeInTheDocument();
    expect(screen.getByText("Dowody są aktualne po odczycie GSC.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Uzupełnij rozpoznanie obiektu" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Odśwież GSC" })).not.toBeInTheDocument();
    expect(screen.queryByText("Wczytuję aktualny plan, wersję roboczą i ograniczenia…")).not.toBeInTheDocument();
    expect(getContentWorkItemSnapshot).not.toHaveBeenCalled();
    expect(postContentWorkItemInitialDraft).not.toHaveBeenCalled();
    expect(postContentWorkItemWordPressDraftExecution).not.toHaveBeenCalled();
    expect(previewAction).not.toHaveBeenCalled();
  });

  it("keeps a terminal connector failure visible without pretending that the context refreshed", async () => {
    const blockedQueue = contentQueueResponse();
    blockedQueue.candidates[0] = {
      ...blockedQueue.candidates[0],
      recommended_mode: "block",
      source_public_url: "https://ekologus.pl/bdo/"
    };
    vi.mocked(getContentWorkItemQueue).mockResolvedValue(blockedQueue);
    vi.mocked(refreshConnector).mockResolvedValue({
      id: "refresh-gsc-bdo-blocked",
      connector_id: "google_search_console",
      connector_label: "Google Search Console",
      mode: "vendor_read",
      status: "blocked",
      status_label: "odczyt zablokowany",
      started_at: "2026-07-22T10:00:00Z",
      completed_at: "2026-07-22T10:00:01Z",
      evidence_ids: [],
      evidence_summary_label: "0 dowodów źródłowych",
      missing_credentials: [],
      checked_credentials: [],
      external_call_attempted: false,
      vendor_data_collected: false,
      metrics_persisted: false,
      metric_summary: {},
      summary: "Odczyt GSC został zablokowany.",
      errors: ["Brakuje dostępu do GSC."],
      redacted: true
    });

    const client = createWilqQueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    fireEvent.click(await screen.findByRole("button", { name: "Odśwież GSC" }));

    expect(await screen.findByText("odczyt zablokowany")).toBeInTheDocument();
    expect(screen.getByText("Brakuje dostępu do GSC.")).toBeInTheDocument();
    expect(getContentWorkItemDecisionContext).toHaveBeenCalledTimes(1);
    expect(getConnectorRefreshRun).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Odśwież GSC" })).toBeEnabled();
    expect(getContentWorkItemSnapshot).not.toHaveBeenCalled();
    expect(postContentWorkItemInitialDraft).not.toHaveBeenCalled();
    expect(postContentWorkItemWordPressDraftExecution).not.toHaveBeenCalled();
  });

  it("retries polling the same in-progress run after a transport error without creating another refresh", async () => {
    const context = contentDecisionContext();
    vi.mocked(refreshConnector).mockResolvedValue({
      id: "refresh-gsc-bdo-transport",
      connector_id: "google_search_console",
      connector_label: "Google Search Console",
      mode: "vendor_read",
      status: "queued",
      status_label: "odczyt w kolejce",
      started_at: "2026-07-22T10:00:00Z",
      completed_at: null,
      evidence_ids: [],
      evidence_summary_label: "0 dowodów źródłowych",
      missing_credentials: [],
      checked_credentials: [],
      external_call_attempted: false,
      vendor_data_collected: false,
      metrics_persisted: false,
      metric_summary: {},
      summary: "Odczyt GSC został dodany do kolejki.",
      errors: [],
      redacted: true
    });
    vi.mocked(getConnectorRefreshRun)
      .mockRejectedValueOnce(new Error("transport"))
      .mockResolvedValueOnce({
        id: "refresh-gsc-bdo-transport",
        connector_id: "google_search_console",
        connector_label: "Google Search Console",
        mode: "vendor_read",
        status: "completed",
        status_label: "odczyt zakończony",
        started_at: "2026-07-22T10:00:00Z",
        completed_at: "2026-07-22T10:00:01Z",
        evidence_ids: ["ev_refresh_gsc_bdo"],
        evidence_summary_label: "1 dowód źródłowy",
        missing_credentials: [],
        checked_credentials: [],
        external_call_attempted: true,
        vendor_data_collected: true,
        metrics_persisted: true,
        metric_summary: {},
        summary: "Odczyt GSC zakończony.",
        errors: [],
        redacted: true
      });

    render(
      <QueryClientProvider client={createWilqQueryClient()}>
        <ContentDecisionContextPanel context={context} />
      </QueryClientProvider>
    );

    fireEvent.click(screen.getByRole("button", { name: "Odśwież GSC" }));
    expect(await screen.findByText("Nie udało się sprawdzić statusu odświeżenia; ponów sprawdzenie tego samego runu.")).toBeInTheDocument();
    expect(refreshConnector).toHaveBeenCalledTimes(1);
    expect(getConnectorRefreshRun).toHaveBeenCalledWith("refresh-gsc-bdo-transport");

    fireEvent.click(screen.getByRole("button", { name: "Sprawdź ponownie status GSC" }));

    await waitFor(() => expect(getConnectorRefreshRun).toHaveBeenCalledTimes(2));
    expect(getConnectorRefreshRun).toHaveBeenLastCalledWith("refresh-gsc-bdo-transport");
    expect(refreshConnector).toHaveBeenCalledTimes(1);
  });

  it("retries only the exact decision context after a completed run when its first refetch fails", async () => {
    const blockedQueue = contentQueueResponse();
    blockedQueue.candidates[0] = {
      ...blockedQueue.candidates[0],
      recommended_mode: "block",
      source_public_url: "https://ekologus.pl/bdo/"
    };
    vi.mocked(getContentWorkItemQueue).mockResolvedValue(blockedQueue);
    const refreshedContext = contentDecisionContext();
    refreshedContext.evidence_readiness = {
      ...refreshedContext.evidence_readiness,
      status: "ready",
      label: "Dowody są aktualne",
      reason: "API zwróciło aktualny kontekst strony.",
      blocker_codes: []
    };
    refreshedContext.next_safe_action = {
      kind: "inspect_object",
      label: "Uzupełnij rozpoznanie obiektu",
      reason: "Brakuje potwierdzonego obiektu WordPress i celu dev.",
      connector_id: null
    };
    vi.mocked(getContentWorkItemDecisionContext)
      .mockResolvedValueOnce(contentDecisionContext())
      .mockRejectedValueOnce(new Error("context transport"))
      .mockResolvedValueOnce(refreshedContext);
    vi.mocked(refreshConnector).mockResolvedValue({
      id: "refresh-gsc-bdo-context",
      connector_id: "google_search_console",
      connector_label: "Google Search Console",
      mode: "vendor_read",
      status: "queued",
      status_label: "odczyt w kolejce",
      started_at: "2026-07-22T10:00:00Z",
      completed_at: null,
      evidence_ids: [],
      evidence_summary_label: "0 dowodów źródłowych",
      missing_credentials: [],
      checked_credentials: [],
      external_call_attempted: false,
      vendor_data_collected: false,
      metrics_persisted: false,
      metric_summary: {},
      summary: "Odczyt GSC został dodany do kolejki.",
      errors: [],
      redacted: true
    });
    vi.mocked(getConnectorRefreshRun).mockResolvedValue({
      id: "refresh-gsc-bdo-context",
      connector_id: "google_search_console",
      connector_label: "Google Search Console",
      mode: "vendor_read",
      status: "completed",
      status_label: "odczyt zakończony",
      started_at: "2026-07-22T10:00:00Z",
      completed_at: "2026-07-22T10:00:01Z",
      evidence_ids: ["ev_refresh_gsc_bdo"],
      evidence_summary_label: "1 dowód źródłowy",
      missing_credentials: [],
      checked_credentials: [],
      external_call_attempted: true,
      vendor_data_collected: true,
      metrics_persisted: true,
      metric_summary: {},
      summary: "Odczyt GSC zakończony.",
      errors: [],
      redacted: true
    });

    const client = createWilqQueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    fireEvent.click(await screen.findByRole("button", { name: "Odśwież GSC" }));
    expect(await screen.findByRole("button", { name: "Sprawdź ponownie kontekst strony" })).toBeEnabled();
    expect(screen.getByText(/Nie udało się ponownie pobrać kontekstu strony/)).toBeInTheDocument();
    expect(refreshConnector).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole("button", { name: "Sprawdź ponownie kontekst strony" }));

    expect(await screen.findByRole("heading", { name: "Uzupełnij rozpoznanie obiektu" })).toBeInTheDocument();
    expect(getContentWorkItemDecisionContext).toHaveBeenCalledTimes(3);
    expect(refreshConnector).toHaveBeenCalledTimes(1);
    expect(screen.queryByText("Sprawdzam ponownie kontekst strony.")).not.toBeInTheDocument();
  });

  it("renders API-owned readiness and material reasons without a status remapper", () => {
    const context = contentDecisionContext();
    context.evidence_readiness = {
      ...context.evidence_readiness,
      status: "ready",
      label: "Dowody są aktualne",
      reason: "Dowody są aktualne dla strony.",
      technical_reason: "Źródło GSC ma aktualny zakres danych.",
      blocker_codes: []
    };
    context.source_public = {
      ...context.source_public,
      identity_status: "observed",
      label: "Adres rozpoznany; materiał niedostępny",
      reason: "WILQ zna publiczny adres, ale materiał tej strony nie jest obecnie dostępny do sprawdzenia.",
      material: {
        ...context.source_public.material,
        status: "blocked",
        caveats: ["Materiał strony nie jest obecnie dostępny do sprawdzenia."]
      }
    };

    render(
      <QueryClientProvider client={createWilqQueryClient()}>
        <ContentDecisionContextPanel context={context} />
      </QueryClientProvider>
    );

    expect(screen.getByText("Dowody są aktualne dla strony.")).toBeInTheDocument();
    expect(screen.queryByText("Dane SEO dla tej strony wymagają odświeżenia przed decyzją.")).not.toBeInTheDocument();
    expect(screen.getByText("Adres rozpoznany; materiał niedostępny")).toBeInTheDocument();
    expect(screen.getByText("WILQ zna publiczny adres, ale materiał tej strony nie jest obecnie dostępny do sprawdzenia.")).toBeInTheDocument();
    expect(screen.queryByText("Publiczny adres i materiał są rozpoznane.")).not.toBeInTheDocument();
  });

  it("shows one API-owned marketer step and keeps technical audit out of the journey", async () => {
    const client = createWilqQueryClient({
      defaultOptions: { queries: { retry: false } }
    });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    const taskMap = await screen.findByTestId(
      "content-workflow-task-map",
      {},
      { timeout: 3_000 }
    );
    const marketerJourney = screen.getByTestId("content-workflow-marketer-journey");
    expect(screen.getByRole("heading", { name: "Treści i SEO" })).toBeInTheDocument();
    expect(within(marketerJourney).getByTestId("content-next-step-hero")).toBeInTheDocument();
    expect(within(taskMap).getAllByRole("button")).toHaveLength(4);
    expect(within(taskMap).getAllByRole("button").filter(
      (button) => button.getAttribute("aria-current") === "step"
    )).toHaveLength(1);
    expect(within(taskMap).getByRole("button", { name: /Tekst/ })).toHaveAttribute(
      "aria-current",
      "step"
    );
    expect(within(taskMap).getByRole("button", { name: /Review/ })).toBeDisabled();
    expect(within(taskMap).getByRole("button", { name: /Odbiór opcjonalny/ })).toBeDisabled();

    expect(within(marketerJourney).getAllByText("BDO dla firm").length).toBeGreaterThan(0);
    expect(
      within(marketerJourney).getByText("BDO i sprawozdawczość środowiskowa")
    ).toBeInTheDocument();
    expect(within(taskMap).getAllByText("Tekst").length).toBeGreaterThan(0);

    expect(screen.getByTestId("content-workflow-marketer-journey")).toBeInTheDocument();
    expect(screen.queryByTestId("content-workflow-technical-audit")).not.toBeInTheDocument();
    expect(screen.queryByText("Decyzje operatora")).not.toBeInTheDocument();
    expect(document.querySelector('[data-active-workspace="draft"]')).toBeInTheDocument();

    expect(saveContentWorkItemSnapshotHumanReview).not.toHaveBeenCalled();
    expect(saveContentWorkItemSnapshotAudit).not.toHaveBeenCalled();
    expect(postContentWorkItemWordPressDraftExecution).not.toHaveBeenCalled();
    expect(saveContentWorkItemDraftRevision).not.toHaveBeenCalled();
    expect(saveContentWorkItemDraftRevisionReview).not.toHaveBeenCalled();
    expect(saveContentWorkItemPlanningReview).not.toHaveBeenCalled();
  });

  it("keeps the first marketer viewport focused on the page, result, reason and current scope", async () => {
    const snapshot = workflowSnapshot({
      currentStepId: "scope",
      steps: operatorStepsAtScope(),
      planning: planningWorkspace({ scopeCurrent: false })
    });
    snapshot.candidate = {
      ...snapshot.candidate,
      title: "BDO – co musi wiedzieć przedsiębiorca?",
      topic: "bdo co to",
      final_canonical_url: "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/",
      search_metrics: {
        impressions: 181,
        clicks: 0,
        ctr: 0,
        query_count: 1,
        primary_query: "bdo co to",
        comparison_status: "not_available",
        comparison_reason: "Brak dwóch porównywalnych okresów."
      }
    };
    snapshot.preflight.item = {
      ...snapshot.preflight.item,
      wordpress_title_or_h1: "BDO – co musi wiedzieć przedsiębiorca?",
      source_public_url: "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/",
      final_canonical_url: "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/",
      metric_facts: []
    };
    vi.mocked(getContentWorkItemSnapshot).mockResolvedValue(snapshot);

    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo", defaultPendingMinMs: 0 })}
        client={createWilqQueryClient({ defaultOptions: { queries: { retry: false } } })}
      />
    );

    const journey = await screen.findByTestId("content-workflow-marketer-journey");
    const picker = within(journey).getByTestId("content-session-picker");
    expect(within(picker).getByRole("heading", { name: "BDO – co musi wiedzieć przedsiębiorca?" })).toBeInTheDocument();
    expect(within(picker).getByText("/bdo-co-musi-wiedziec-przedsiebiorca/")).toBeInTheDocument();
    expect(within(picker).getByText("BDO i sprawozdawczość środowiskowa")).toBeInTheDocument();
    expect(within(journey).getByText("Wersja robocza HTML do review")).toBeInTheDocument();
    expect(within(journey).getByText("Powstanie po domknięciu aktualnego zakresu.")).toBeInTheDocument();
    const hero = within(journey).getByTestId("content-next-step-hero");
    expect(within(hero).getByText("Tekst")).toBeInTheDocument();
    expect(within(hero).getByRole("button", { name: "Sprawdź stan draftu" })).toBeInTheDocument();
    expect(within(journey).getByText(/Dostępny odczyt GSC: 181 wyświetleń i 0 kliknięć/)).toBeInTheDocument();
    expect(within(journey).getByText(/Brak exact danych GA4 ogranicza ocenę efektu/)).toBeInTheDocument();
    expect(within(journey).queryByLabelText("Najważniejsze dane dla strony")).not.toBeInTheDocument();
    expect(within(journey).queryByLabelText("Fakty, sygnały i blokady")).not.toBeInTheDocument();

    fireEvent.click(within(journey).getByRole("button", { name: "Otwórz źródła i ograniczenia strony" }));
    expect(await screen.findByTestId("content-workflow-sources-view")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Wróć do treści i SEO" }));
    expect(await screen.findByTestId("content-workflow-marketer-journey")).toBeInTheDocument();
    expect(within(screen.getByTestId("content-session-picker")).getByText("/bdo-co-musi-wiedziec-przedsiebiorca/")).toBeInTheDocument();
    expect(saveContentWorkItemPlanningReview).not.toHaveBeenCalled();
    expect(saveContentWorkItemDraftRevision).not.toHaveBeenCalled();
    expect(postContentWorkItemCodexSectionProposal).not.toHaveBeenCalled();
    expect(postContentWorkItemWordPressDraftExecution).not.toHaveBeenCalled();
  });

  it("shows the real knowledge corpus blocker before a plan can be generated", async () => {
    vi.mocked(getKnowledgeSourceMaterials).mockResolvedValue([
      {
        source_id: "source-transcript-1",
        file_name: "rozmowa-z-ekologus.txt",
        title: "Rozmowa z zespołem Ekologus",
        kind: "transcript",
        word_count: 1200,
        digest_prefix: "abc123",
        privacy_class: "internal",
        import_status: "import_pending",
        source_path: "/private/rozmowa-z-ekologus.txt"
      }
    ]);
    vi.mocked(getKnowledgeSourceMaterialReadiness).mockResolvedValue({
      status: "import_pending",
      total_count: 15,
      imported_count: 7,
      import_pending_count: 8,
      excerpt_review_required_count: 0,
      ready_for_generation: false,
      blocker: "Pozostałe materiały oczekują na import.",
      next_step: "Dokończ kontrolowany import materiałów.",
      imported_materials: [],
      pending_materials: [
        {
          source_id: "source-transcript-1",
          file_name: "rozmowa-z-ekologus.txt",
          title: "Rozmowa z zespołem Ekologus",
          kind: "transcript",
          word_count: 1200,
          digest_prefix: "abc123",
          privacy_class: "internal",
          import_status: "import_pending",
          source_path: "/private/rozmowa-z-ekologus.txt"
        }
      ],
      excerpt_review_materials: []
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

    const notice = await screen.findByTestId("content-workflow-knowledge-readiness");
    expect(notice).toHaveTextContent("Zaimportowano 7 z 15 materiałów");
    expect(notice).toHaveTextContent("8 oczekuje na kontrolowany import");
    expect(notice).toHaveTextContent("Dokończ kontrolowany import materiałów.");
    expect(notice).toHaveTextContent("Materiały oczekujące na obsługę");
    expect(notice).toHaveTextContent("Rozmowa z zespołem Ekologus");
    expect(notice).not.toHaveTextContent("/private/rozmowa-z-ekologus.txt");
  });

  it("shows the approved source manifest when generation is ready", async () => {
    vi.mocked(getKnowledgeSourceMaterials).mockResolvedValue([
      {
        source_id: "source-approved-transcript",
        file_name: "rozmowa-ekologus.txt",
        title: "Rozmowa z zespołem Ekologus",
        kind: "transcript",
        word_count: 1840,
        digest_prefix: "abc123",
        privacy_class: "internal",
        import_status: "imported",
        source_path: "/private/rozmowa-ekologus.txt"
      }
    ]);
    const client = createWilqQueryClient({
      defaultOptions: { queries: { retry: false } }
    });

    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    const sources = await screen.findByTestId("content-workflow-knowledge-sources");
    expect(sources).toHaveTextContent("Materiały źródłowe używane przez WILQ (1)");
    expect(sources).toHaveTextContent("Rozmowa z zespołem Ekologus");
    expect(sources).toHaveTextContent("transcript · 1840 słów · zaimportowany");
    expect(sources).not.toHaveTextContent("/private/rozmowa-ekologus.txt");
  });

  it("distinguishes excerpt review from pending import in corpus readiness", async () => {
    vi.mocked(getKnowledgeSourceMaterialReadiness).mockResolvedValue({
      status: "excerpt_review_required",
      total_count: 15,
      imported_count: 13,
      import_pending_count: 0,
      excerpt_review_required_count: 2,
      ready_for_generation: false,
      blocker: "Dwa excerpty wymagają review.",
      next_step: "Zatwierdź excerpty i ich lineage."
    });
    const client = createWilqQueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    const notice = await screen.findByTestId("content-workflow-knowledge-readiness");
    expect(notice).toHaveTextContent("2 wymaga review excerptów");
    expect(notice).toHaveTextContent("Zatwierdź excerpty i ich lineage.");
    expect(notice).not.toHaveTextContent("kontrolowany import");
  });

  it("keeps a non-ready corpus actionable when the API omits its next step", async () => {
    vi.mocked(getKnowledgeSourceMaterialReadiness).mockResolvedValue({
      status: "import_pending",
      total_count: 0,
      imported_count: 0,
      import_pending_count: 0,
      excerpt_review_required_count: 0,
      ready_for_generation: false,
      blocker: "Korpus wymaga obsługi.",
      next_step: ""
    });
    const client = createWilqQueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    expect(await screen.findByTestId("content-workflow-knowledge-readiness")).toHaveTextContent(
      "Skontaktuj się z administratorem"
    );
  });

  it("does not silently treat a readiness fetch error as generation-ready", async () => {
    vi.mocked(getKnowledgeSourceMaterialReadiness).mockRejectedValue(new Error("offline"));
    const client = createWilqQueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    expect(await screen.findByTestId("content-workflow-knowledge-readiness-error"))
      .toHaveTextContent("Nie udało się odczytać gotowości korpusu");
  });

  it.skip("does not present an old proposal as ready when planning input is blocked", async () => {
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
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo", defaultPendingMinMs: 0 })}
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
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo", defaultPendingMinMs: 0 })}
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

    const picker = await screen.findByRole("combobox", { name: "Strona" });
    expect(within(picker).getAllByRole("option")).toHaveLength(3);
    expect(picker).toHaveValue("content_work_item_bdo");

    const pageSearch = screen.getByRole("searchbox", { name: "Szukaj strony" });
    fireEvent.change(pageSearch, { target: { value: "zielony ład" } });
    expect(within(picker).getByRole("option", { name: /Zielony Ład/i })).toBeInTheDocument();
    expect(within(picker).getByRole("option", { name: /bdo/i })).toBeInTheDocument();
    fireEvent.change(pageSearch, { target: { value: "" } });

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

  it("keeps an unknown deep link on the explicit selection screen", async () => {
    render(
      <App
        appRouter={createWilqRouter({
          initialPath: "/content-workflow?work_item_id=missing_work_item",
          defaultPendingMinMs: 0
        })}
        client={createWilqQueryClient({ defaultOptions: { queries: { retry: false } } })}
      />
    );

    expect(await screen.findByText("Wybierz stronę do pracy")).toBeInTheDocument();
    expect(screen.queryByRole("combobox", { name: "Strona" })).not.toBeInTheDocument();
    expect(getContentWorkItemSnapshot).not.toHaveBeenCalled();
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

    const picker = await screen.findByRole("combobox", { name: "Strona" });
    expect(picker).toHaveValue("content_work_item_bdo");

    fireEvent.change(picker, { target: { value: "content_work_item_green_deal" } });
    await waitFor(() =>
      expect(screen.getByRole("combobox", { name: "Strona" })).toHaveValue(
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
      expect(screen.getByRole("combobox", { name: "Strona" })).toHaveValue(
        "content_work_item_bdo"
      )
    );
  });

  it("shows the generated page as a read-only result without a duplicate section editor", async () => {
    vi.mocked(getContentWorkItemSnapshot).mockResolvedValue(
      workflowSnapshot({
        workspace: savedRevisionWorkspace(savedFullDraftRevision()),
        currentStepId: "draft"
      })
    );
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

    expect(await screen.findByText(/Pełny draft HTML/)).toBeInTheDocument();
    expect(screen.getByTestId("content-full-draft-preview")).toBeInTheDocument();
    expect(screen.queryByRole("combobox", { name: "Sekcja dokumentu" })).not.toBeInTheDocument();
    expect(screen.queryByRole("textbox", { name: /HTML sekcji/ })).not.toBeInTheDocument();
    expect(saveContentWorkItemPlanningReview).not.toHaveBeenCalled();
    expect(saveContentWorkItemDraftRevision).not.toHaveBeenCalled();
    expect(postContentWorkItemCodexSectionProposal).not.toHaveBeenCalled();
    expect(postContentWorkItemWordPressDraftExecution).not.toHaveBeenCalled();
  });

  it("keeps page discovery secondary and does not ask for a section during scope", async () => {
    vi.mocked(getContentWorkItemSnapshot).mockResolvedValue(workflowSnapshot({ currentStepId: "scope" }));
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo", defaultPendingMinMs: 0 })}
        client={createWilqQueryClient({ defaultOptions: { queries: { retry: false } } })}
      />
    );

    const picker = await screen.findByTestId("content-session-picker");
    expect(within(picker).getByLabelText("Strona")).toBeInTheDocument();
    expect(within(picker).queryByRole("combobox", { name: "Przejdź do sekcji strony" })).not.toBeInTheDocument();
    expect(within(picker).queryByRole("combobox", { name: "Przejdź do sekcji z planu" })).not.toBeInTheDocument();
  });

  it("exposes a full-inventory page outside the opportunity queue", async () => {
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo", defaultPendingMinMs: 0 })}
        client={createWilqQueryClient({ defaultOptions: { queries: { retry: false } } })}
      />
    );

    const picker = await screen.findByRole("combobox", { name: "Strona" });
    expect(within(picker).getByRole("option", { name: /Raportowanie odpadowe/ })).toBeInTheDocument();

    expect(within(picker).getByRole("option", { name: /Raportowanie odpadowe/ })).toHaveValue(
      "content_work_item_inventory_full_catalog"
    );
  });

  it("opens a selected full-inventory page through the same workflow seam", async () => {
    const inventoryCandidate: ContentWorkItemQueueResponse["candidates"][number] = {
      ...contentQueueResponse().candidates[0],
      work_item_id: "content_work_item_inventory_full_catalog",
      decision_id: "decision_inventory_full_catalog",
      title: "Raportowanie odpadowe",
      topic: "Raportowanie odpadowe",
      status_label: "gotowe do planu",
      source_public_url: "https://www.ekologus.pl/raportowanie-odpadowe/",
      final_canonical_url: "https://www.ekologus.pl/raportowanie-odpadowe/",
      intended_final_url: "https://www.ekologus.pl/raportowanie-odpadowe/",
      preview_url: "https://ekologus.dev.proudsite.pl/raportowanie-odpadowe/",
      page_inventory: {
        ...contentQueueResponse().candidates[0].page_inventory!,
        title_or_h1: "Raportowanie odpadowe",
        section_count: 0,
        section_headings: [],
        acf_section_inventory_status: "missing",
        acf_section_headings: []
      }
    };
    vi.mocked(getContentWorkItemQueue).mockImplementation(async (workItemId) =>
      workItemId === inventoryCandidate.work_item_id
        ? { ...contentQueueResponse(), candidates: [inventoryCandidate], candidate_count: 1 }
        : contentQueueResponse()
    );
    vi.mocked(getContentWorkItemSnapshot).mockResolvedValue(
      workflowSnapshot({
        candidate: inventoryCandidate,
        item: workItem({
          wordpress_title_or_h1: "Raportowanie odpadowe",
          source_public_url: inventoryCandidate.source_public_url,
          final_canonical_url: inventoryCandidate.final_canonical_url
        })
      })
    );

    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo", defaultPendingMinMs: 0 })}
        client={createWilqQueryClient({ defaultOptions: { queries: { retry: false } } })}
      />
    );

    const picker = await screen.findByRole("combobox", { name: "Strona" });
    fireEvent.change(picker, { target: { value: inventoryCandidate.work_item_id } });

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Raportowanie odpadowe" })).toBeInTheDocument();
      expect(picker).toHaveValue(inventoryCandidate.work_item_id);
    });
    expect(getContentWorkItemQueue).toHaveBeenCalledWith(inventoryCandidate.work_item_id);
  });

  it("uses current page headings before a plan exists", async () => {
    const snapshot = workflowSnapshot();
    snapshot.planning_workspace!.proposal.sections = [];
    vi.mocked(getContentWorkItemSnapshot).mockResolvedValueOnce(snapshot);

    render(
      <App
        appRouter={createWilqRouter({
          initialPath: "/content-workflow?work_item_id=content_work_item_bdo",
          defaultPendingMinMs: 0
        })}
        client={createWilqQueryClient({ defaultOptions: { queries: { retry: false } } })}
      />
    );

    const sectionPicker = await screen.findByRole("combobox", { name: "Przejdź do sekcji strony" });
    expect(within(sectionPicker).getAllByRole("option")).toHaveLength(2);
    expect(sectionPicker).toHaveValue("Kogo dotyczy BDO");
    expect(within(sectionPicker).getByRole("option", { name: "Jak przygotować dokumenty" })).toBeInTheDocument();
  });

  it("starts dynamic planning only from the explicit strategy action", async () => {
    vi.mocked(getContentWorkItemPlanningProposal).mockResolvedValueOnce(
      planningProposalStatus({
        proposal: {
          ...planningWorkspace().proposal,
          service_card_id: "ekologus_service_bdo_reporting",
          service_selection_confirmed: true
        } as never
      })
    );
    vi.mocked(getContentWorkItemSnapshot).mockResolvedValue(
      workflowSnapshot({
      planning: planningWorkspace({ scopeCurrent: true, sectionMapCurrent: false }),
        workspace: { ...revisionWorkspace(), can_save: false },
        currentStepId: "scope",
        steps: operatorStepsAtScope()
      })
    );
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo", defaultPendingMinMs: 0 })}
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
    expect(screen.getByText("Pokaż dokładne fakty i porównania metryk")).toBeInTheDocument();
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
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo", defaultPendingMinMs: 0 })}
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

  it("refreshes an incomplete legacy revision without replacing its history", async () => {
    const planning = planningWorkspace({ generated: true });
    const legacy = savedDraftRevision();
    const refreshed = savedFullDraftRevision();
    vi.mocked(postContentWorkItemInitialDraft).mockResolvedValue(
      initialDraftResponse(refreshed)
    );
    vi.mocked(getContentWorkItemSnapshot)
      .mockResolvedValueOnce(
        workflowSnapshot({
          planning,
          workspace: { ...savedRevisionWorkspace(legacy), context_current: false },
          currentStepId: "draft"
        })
      )
      .mockResolvedValue(
        workflowSnapshot({
          planning,
          workspace: savedRevisionWorkspace(refreshed),
          currentStepId: "draft"
        })
      );

    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo", defaultPendingMinMs: 0 })}
        client={createWilqQueryClient({ defaultOptions: { queries: { retry: false } } })}
      />
    );

    const panel = await screen.findByTestId("content-draft-workbench");
    expect(within(panel).getByText("Pełny draft HTML — niegotowy")).toBeInTheDocument();
    const refreshButton = within(panel).getByRole("button", { name: "Odśwież pełny draft" });
    expect(refreshButton).toBeEnabled();
    fireEvent.click(refreshButton);
    await waitFor(() => expect(postContentWorkItemInitialDraft).toHaveBeenCalledWith(
      {
        expected_proposal_id: "content_planning_proposal_bdo",
        expected_planning_digest: "a".repeat(64),
        expected_planning_input_digest: "f".repeat(64),
        requested_by: "wilku"
      },
      "content_work_item_bdo"
    ));
    expect(await screen.findByTestId("content-full-page-preview")).toBeInTheDocument();
    expect(screen.getByText("Pełny draft HTML do review")).toBeInTheDocument();
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
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    expect(await screen.findByText("Decyzja dla tej strony")).toBeInTheDocument();
    expect(screen.getByText("Główna intencja")).toBeInTheDocument();
    expect(screen.getByText("właściciel firmy")).toBeInTheDocument();
    expect(screen.queryByText("Co robisz teraz?")).not.toBeInTheDocument();
    expect(screen.getByText("Pokaż szczegóły zakresu i źródła")).toBeInTheDocument();
    const saveScopeButton = screen.getByRole("button", { name: "Zapisz decyzję" });
    expect(saveScopeButton).not.toBeDisabled();
    fireEvent.click(saveScopeButton);

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
    expect(await screen.findByText("Kontekst planu")).toBeInTheDocument();
    expect(screen.getByTestId("content-planning-generation")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Otwórz kontekst planu" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Przejdź do tekstu" })).not.toBeInTheDocument();
    expect(screen.queryByTestId("content-draft-editor")).not.toBeInTheDocument();
    expect(screen.queryByText("Automatyczna mapa sekcji")).not.toBeInTheDocument();
    expect(screen.queryByText("Aktualna strona")).not.toBeInTheDocument();
    expect(postContentWorkItemWordPressDraftExecution).not.toHaveBeenCalled();
  });

  it("opens text automatically when the refreshed section map becomes current", async () => {
    const pendingMap = planningWorkspace({ scopeCurrent: true, sectionMapCurrent: false });
    const readyMap = planningWorkspace({ scopeCurrent: true, sectionMapCurrent: true, generated: true });
    vi.mocked(getContentWorkItemSnapshot)
      .mockResolvedValueOnce(
        workflowSnapshot({
          planning: pendingMap,
          currentStepId: "section_map",
          steps: operatorStepsAtSectionMap()
        })
      )
      .mockResolvedValue(
        workflowSnapshot({
          planning: readyMap,
          currentStepId: "section_map",
          steps: operatorStepsAtSectionMap()
        })
      );
    const client = createWilqQueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    expect(await screen.findByRole("button", { name: /1\. Kontekst/ })).toHaveAttribute("aria-pressed", "true");
    await client.invalidateQueries({ queryKey: ["content-workflow", "work-item", "content_work_item_bdo"] });

    await waitFor(() => {
      expect(screen.getByTestId("content-draft-workbench")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /2\. Tekst/ })).toHaveAttribute("aria-current", "step");
    });
    expect(screen.queryByText("Plan sekcji")).not.toBeInTheDocument();
    expect(postContentWorkItemWordPressDraftExecution).not.toHaveBeenCalled();
  });

  it("opens text when a generated map is current even if the raw API step remains scope", async () => {
    const readyMap = planningWorkspace({ scopeCurrent: false, sectionMapCurrent: true, generated: true });
    vi.mocked(getContentWorkItemSnapshot).mockResolvedValue(
      workflowSnapshot({
        planning: readyMap,
        currentStepId: "scope",
        steps: operatorStepsAtScope()
      })
    );

    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo", defaultPendingMinMs: 0 })}
        client={createWilqQueryClient({ defaultOptions: { queries: { retry: false } } })}
      />
    );

    expect(await screen.findByTestId("content-draft-workbench")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /2\. Tekst/ })).toHaveAttribute("aria-current", "step");
    expect(screen.queryByText("Plan sekcji")).not.toBeInTheDocument();
    expect(screen.queryByText(/Najpierw zakończ wcześniejszy krok/)).not.toBeInTheDocument();
  });

  it("makes a stale planning decision explicit instead of presenting it as approved", async () => {
    const planning = planningWorkspace({
      scopeCurrent: false,
      sectionMapCurrent: false,
      staleScopeDecision: true
    });
    vi.mocked(getContentWorkItemSnapshot).mockResolvedValue(
      workflowSnapshot({
        planning,
        workspace: { ...revisionWorkspace(), can_save: false },
        currentStepId: "scope",
        steps: operatorStepsAtScope()
      })
    );

    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo", defaultPendingMinMs: 0 })}
        client={createWilqQueryClient({ defaultOptions: { queries: { retry: false } } })}
      />
    );

    expect(await screen.findByText("Poprzednia decyzja dotyczy starszego zakresu")).toBeInTheDocument();
    expect(screen.queryByText("Ostatnia decyzja: zaakceptowano · nieaktualna")).not.toBeInTheDocument();
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
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    await screen.findByText("Sprawdź zakres strony");
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
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    const sectionInput = await screen.findByLabelText("HTML sekcji Kogo dotyczy BDO");
    expect(sectionInput).toHaveValue("<p>Zapisana treść pierwszej wersji o obowiązkach BDO.</p>");
    const editedHtml = '<p data-proof="saved-html">Poprawiona treść drugiej wersji zachowana przez workspace.</p>';
    fireEvent.change(sectionInput, { target: { value: editedHtml } });
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
            content_html: editedHtml,
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
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    const sectionInput = await screen.findByLabelText("HTML sekcji Kogo dotyczy BDO");
    const localText = "Moje lokalne poprawki nie mogą zniknąć po konflikcie.";
    const localHtml = `<p>${localText}</p>`;
    fireEvent.change(sectionInput, { target: { value: localHtml } });
    fireEvent.click(screen.getByRole("button", { name: "Zapisz poprawioną wersję do review" }));

    const conflict = await screen.findByTestId("save-revision-conflict");
    expect(conflict).toHaveTextContent("Twój tekst pozostał w edytorze");
    expect(conflict).toHaveTextContent("Porównaj wersję 2 i scal zmiany ręcznie");
    expect(sectionInput).toHaveValue(localHtml);
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
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    const sectionInput = await screen.findByLabelText("HTML sekcji Kogo dotyczy BDO");
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
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    expect(await screen.findByText(`Aktualny draft: ${revision.title}`))
      .toBeInTheDocument();
    const immutableContent = screen.getByTestId("immutable-revision-content");
    expect(within(immutableContent).getByText(revision.sections[0]?.body_markdown ?? ""))
      .toBeInTheDocument();
    expect(within(immutableContent).getAllByText(/ev_gsc_bdo/).length).toBeGreaterThan(0);
    expect(
      screen.getByRole("button", {
        name: "Zapisz decyzję dla aktualnego draftu"
      })
    ).toBeDisabled();
    expect(screen.getByText(/Dodaj krótką notatkę/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Decyzja dla wersji szkicu"), {
      target: { value: "approved" }
    });
    const approveButton = screen.getByRole("button", {
      name: "Zapisz decyzję dla aktualnego draftu"
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

  it("labels a saved revision as stale when the workflow context changed", async () => {
    const revision = savedDraftRevision();
    vi.mocked(getContentWorkItemSnapshot).mockResolvedValue(
      workflowSnapshot({
        workspace: {
          ...savedRevisionWorkspace(revision),
          context_current: false
        },
        currentStepId: "draft"
      })
    );
    const client = createWilqQueryClient({
      defaultOptions: { queries: { retry: false } }
    });

    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    expect(await screen.findByText("Zapisana wersja · wymaga odświeżenia")).toBeInTheDocument();
    expect(screen.queryByText("Aktualny draft · wersja zapisana")).not.toBeInTheDocument();
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
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    expect(await screen.findByText("Advisory review semantyczne")).toBeInTheDocument();
    expect(screen.getByText("Przeczytaj podgląd całej strony.")).toBeInTheDocument();
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
    fireEvent.click(screen.getByRole("button", { name: "Zapisz decyzję dla aktualnego draftu" }));

    await waitFor(() => expect(getContentWorkItemSnapshot).toHaveBeenCalledTimes(2));
    await waitFor(() =>
      expect(screen.queryByText("Odpowiedź zaczyna się zbyt ogólnie")).not.toBeInTheDocument()
    );
    expect(postContentWorkItemWordPressDraftExecution).not.toHaveBeenCalled();
    expect(postContentWorkItemWordPressAuthoringPayloadPreview).not.toHaveBeenCalled();
  });

  it("does not offer a retry when semantic review storage is not activated", async () => {
    const revision = savedFullDraftRevision();
    vi.mocked(getContentWorkItemSnapshot).mockResolvedValue(
      workflowSnapshot({
        workspace: savedRevisionWorkspace(revision),
        currentStepId: "review",
        steps: operatorStepsAtReview()
      })
    );
    vi.mocked(getContentWorkItemSemanticReview).mockResolvedValue({
      ...semanticReviewNotGenerated(revision),
      status: "blocked",
      blockers: [{
        code: "storage_activation_required",
        label: "Storage reviewu nieaktywne",
        reason: "Realny local state nie ma aktywowanej tabeli semantic review.",
        next_step: "Wykonaj zatwierdzone okno maintenance.",
        source_codes: ["content_semantic_reviews"]
      }]
    });
    const client = createWilqQueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } }
    });

    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    const button = await screen.findByRole("button", { name: "Automatyczne sprawdzenie chwilowo niedostępne" });
    expect(button).toBeDisabled();
    expect(screen.getByText(/Automatyczne sprawdzenie tekstu jest chwilowo niedostępne/)).toBeInTheDocument();
    expect(postContentWorkItemSemanticReview).not.toHaveBeenCalled();
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
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    await waitFor(() => expect(getAction).toHaveBeenCalledWith("act_apply_wordpress_draft_handoff"));
    await screen.findByText("Szkic aktualnego tekstu → dev");
    expect(screen.getByText("WordPress · gotowy szkic na devie")).toBeInTheDocument();
    const wizard = screen.getByTestId("content-wordpress-draft-action-wizard");
    expect(within(wizard).getByText("Szkic aktualnego tekstu → dev")).toBeInTheDocument();
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

  it("switches between marketer mode and read-only sources mode", async () => {
    const client = createWilqQueryClient({
      defaultOptions: { queries: { retry: false } }
    });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    expect(await screen.findByTestId("content-workflow-marketer-journey")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Otwórz źródła i ograniczenia strony" }));
    expect(screen.getByTestId("content-workflow-sources-view")).toBeInTheDocument();
    expect(screen.queryByTestId("content-workflow-marketer-journey")).not.toBeInTheDocument();
    expect(screen.getByText("Źródła i ograniczenia")).toBeInTheDocument();
    expect(screen.getByText("Widok read-only")).toBeInTheDocument();
    expect(screen.queryByText("Workflow treści")).not.toBeInTheDocument();
    expect(screen.queryByText("Następny krok")).not.toBeInTheDocument();
    expect(screen.queryByText("Co blokuje publikację")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Wróć do treści i SEO" }));
    expect(await screen.findByTestId("content-workflow-marketer-journey")).toBeInTheDocument();
  });

  it.skip("keeps the queue decision visible while the selected workflow snapshot loads", async () => {
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
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    await waitFor(() => {
      expect(getContentWorkItemSnapshot).toHaveBeenCalledWith("content_work_item_bdo");
    });
    expect(screen.getAllByText("Treści i SEO").length).toBeGreaterThan(0);
    expect(screen.getAllByText("BDO dla firm").length).toBeGreaterThan(0);
    expect(screen.getByText("Ładowanie szczegółów workflow")).toBeInTheDocument();
    expect(screen.queryByText("Ładowanie stanu WILQ")).not.toBeInTheDocument();

    resolveSnapshot?.(workflowSnapshot());
    expect(await screen.findByTestId("content-workflow-task-map")).toBeInTheDocument();
  });

  it.skip("does not expose the legacy draft-package approval control", async () => {
    const client = createWilqQueryClient({
      defaultOptions: { queries: { retry: false } }
    });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo", defaultPendingMinMs: 0 })}
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

  it.skip("sends a human-selected advisory section by stable ID", async () => {
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
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo", defaultPendingMinMs: 0 })}
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

  it.skip("does not expose the legacy package-bound audit control", async () => {
    vi.mocked(getContentWorkItemSnapshot).mockResolvedValue(workflowSnapshot({ review: humanReview() }));
    const client = createWilqQueryClient({
      defaultOptions: { queries: { retry: false } }
    });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    await openWorkflowDetails();
    expect(screen.queryByRole("button", { name: "Zapisz audyt przekazania" }))
      .not.toBeInTheDocument();
    expect(saveContentWorkItemSnapshotHumanReview).not.toHaveBeenCalled();
    expect(postContentWorkItemWordPressDraftExecution).not.toHaveBeenCalled();
  });

  it("keeps section editing and Codex assistance out of the marketer result view", async () => {
    const revision = savedDraftRevision();
    vi.mocked(getContentWorkItemSnapshot).mockResolvedValue(
      workflowSnapshot({ workspace: needsChangesRevisionWorkspace(revision) })
    );
    const client = createWilqQueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } }
    });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    expect(await screen.findByText(/Pełny draft HTML/)).toBeInTheDocument();
    expect(screen.queryByRole("textbox", { name: /HTML sekcji/ })).not.toBeInTheDocument();
    expect(screen.queryByText("Popraw aktualny tekst z Codexem")).not.toBeInTheDocument();
    expect(postContentWorkItemWordPressDraftExecution).not.toHaveBeenCalled();
    expect(postContentWorkItemWordPressAuthoringPayloadPreview).not.toHaveBeenCalled();
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

  it.skip("shows API-owned blockers when a queue candidate cannot enter the gated workflow", async () => {
    const client = createWilqQueryClient({
      defaultOptions: { queries: { retry: false } }
    });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo", defaultPendingMinMs: 0 })}
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
    expect(screen.getByText("wstrzymaj — najpierw sprawdź")).toBeInTheDocument();
    expect(screen.getByText("pomiar zablokowany")).toBeInTheDocument();
  });

  it.skip("shows dry-run ACF field mapping after the WordPress handoff exists", async () => {
    vi.mocked(getContentWorkItemSnapshot).mockResolvedValue(
      workflowSnapshot({ review: humanReview(), handoff: wordpressHandoff() })
    );
    const client = createWilqQueryClient({
      defaultOptions: { queries: { retry: false } }
    });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo", defaultPendingMinMs: 0 })}
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

  it.skip("disables technical WordPress dry-runs when API readiness is blocked", async () => {
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
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo", defaultPendingMinMs: 0 })}
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

  it.skip("previews edited section text without requesting a direct WordPress write", async () => {
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
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo", defaultPendingMinMs: 0 })}
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

  it.skip("shows remembered dev WordPress draft from the activation packet", async () => {
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
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    expect(await screen.findByText(/Pełny draft HTML/)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Otwórz podgląd na dev" })).not.toBeInTheDocument();
    await openWorkflowDetails();
    expect(screen.getByText(/Szkic utworzony na devie jako WordPress draft, ID 987/))
      .toBeInTheDocument();
    expect(screen.getByText("Odczyt z dev WordPress")).toBeInTheDocument();
    expect(screen.getAllByText(/BDO dla firm - szkic dev/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Szkic opisuje obowiązki BDO/).length).toBeGreaterThan(0);
    expect(screen.getByText("glowny_opis")).toBeInTheDocument();
    expect(screen.getByText("Plan treści i mapowanie")).toBeInTheDocument();
    expect(screen.getAllByText(/Co to jest BDO/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Kogo dotyczy BDO/).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Przygotuj mapowanie sekcji ACF" }))
      .toBeEnabled();
    expect(postContentWorkItemWordPressDraftExecution).not.toHaveBeenCalled();
  });

  it.skip("prepares ACF mapping from the section writing workbench", async () => {
    vi.mocked(getContentWorkItemSnapshot).mockResolvedValue(
      workflowSnapshot({ review: humanReview(), handoff: wordpressHandoff() })
    );
    const client = createWilqQueryClient({
      defaultOptions: { queries: { retry: false } }
    });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo", defaultPendingMinMs: 0 })}
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
  fireEvent.click(await screen.findByRole("button", { name: "Otwórz źródła i ograniczenia strony" }));
  await screen.findByTestId("content-workflow-sources-view");
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
    content_inventory_status: "available",
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
    source_fact_ids: ["ekologus_public_bdo_faq_2026_07_01"],
    source_material_ids: [],
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
    metric_facts: [
      {
        name: "active_users",
        metric_label: "aktywni użytkownicy",
        value: 26,
        period: "2026-06-22/2026-07-19",
        source_connector: "google_analytics_4",
        evidence_id: "ev_ga4_bdo",
        dimensions: { source_medium: "google / organic" },
        dimension_labels: {},
        dimension_value_labels: {}
      },
      {
        name: "active_users",
        metric_label: "aktywni użytkownicy",
        value: 12,
        period: "2026-06-22/2026-07-19",
        source_connector: "google_analytics_4",
        evidence_id: "ev_ga4_bdo",
        dimensions: { source_medium: "google / cpc" },
        dimension_labels: {},
        dimension_value_labels: {}
      },
      {
        name: "engagement_rate",
        metric_label: "wskaźnik zaangażowania",
        value: 0.42,
        period: "2026-06-22/2026-07-19",
        source_connector: "google_analytics_4",
        evidence_id: "ev_ga4_bdo",
        dimensions: { source_medium: "google / organic" },
        dimension_labels: {},
        dimension_value_labels: {}
      }
    ],
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

function contentInventoryCatalog(): ContentInventoryCatalogResponse {
  return {
    status: "ready",
    total_count: 1,
    ready_count: 1,
    partial_count: 0,
    blocked_count: 0,
    items: [
      {
        catalog_id: "catalog_full_inventory",
        work_item_id: "content_work_item_inventory_full_catalog",
        url: "https://www.ekologus.pl/raportowanie-odpadowe/",
        path: "/raportowanie-odpadowe/",
        title: "Raportowanie odpadowe",
        content_type: "page",
        content_summary: "Raportowanie odpadowe",
        content_word_count: 240,
        section_count: 0,
        acf_section_count: 0,
        acf_field_names: [],
        acf_section_headings: [],
        material_status: "content_summary",
        source_connector: "wordpress_ekologus",
        evidence_id: "ev_wp_full_catalog",
        collected_at: "2026-07-20T00:00:00Z",
        metrics_status: "missing",
        metrics_evidence_ids: [],
        metrics_query_count: 0,
        metrics_clicks: 0,
        metrics_impressions: 0
      }
    ],
    source_connectors: ["wordpress_ekologus"],
    evidence_ids: ["ev_wp_full_catalog"],
    coverage: {
      status: "complete",
      source_count: 1,
      returned_count: 1,
      public_sitemap_source_count: 1,
      public_sitemap_returned_count: 1,
      public_sitemap_truncated: false,
      caveat: ""
    }
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
        page_inventory: {
          title_or_h1: "BDO dla firm",
          section_count: 2,
          section_headings: ["Kogo dotyczy BDO", "Jak przygotować dokumenty"],
          section_inventory_status: "available",
          content_inventory_status: "available",
          acf_section_inventory_status: "missing",
          acf_section_headings: []
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
        recommended_mode_label: "wstrzymaj — najpierw sprawdź",
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

function staleGscFreshnessAssessment() {
  return {
    ...contentFreshnessAssessment(),
    state: "stale" as const,
    state_label: "wymaga odświeżenia",
    requires_refresh: true,
    stale_connector_ids: ["google_search_console"],
    connector_labels_requiring_refresh: ["Google Search Console"],
    summary: "GSC jest nieświeże dla tej decyzji.",
    next_step: "Odśwież Google Search Console."
  };
}

function contentDecisionContext(): ContentDecisionContext {
  return {
    response_type: "content_decision_context",
    contract_version: "content_decision_context_v1",
    work_item_id: "content_work_item_bdo",
    work_kind: "refresh_existing",
    source_public: {
      identity_status: "partial",
      object_id: null,
      url: "https://ekologus.pl/bdo/",
      title: "BDO dla firm",
      post_type: null,
      post_status: null,
      template: null,
      material: {
        status: "available",
        source_kind: "wordpress_rest",
        observed_surfaces: ["wordpress_rest_content"],
        word_count: 120,
        section_count: 2,
        evidence_ids: ["ev_wp_bdo"],
        caveats: ["Odczyt materiału nie jest mapą targetu dev."]
      },
      label: "Adres i materiał rozpoznane częściowo",
      reason: "WILQ widzi publiczny adres i materiał, ale nie potwierdził jeszcze konkretnego obiektu WordPress ani miejsca przygotowania zmiany.",
      technical_reason: "WILQ zna adres i materiał, ale obecny kontrakt inventory nie zachowuje exact tożsamości obiektu WordPress."
    },
    authoring_target: {
      mapping_status: "unverified",
      environment: "staging",
      object_id: null,
      post_type: null,
      post_status: null,
      template: null,
      authoring_surfaces: [],
      allowed_operation: "create_wordpress_draft",
      label: "Target dev niepotwierdzony",
      reason: "Brakuje potwierdzonego celu dev dla tej strony.",
      technical_reason: "Globalny profil WordPress nie mapuje tej strony do obiektu dev."
    },
    source_target_relation: {
      status: "unverified",
      relation_type: "unknown",
      label: "Relacja source → target niepotwierdzona",
      reason: "Brakuje potwierdzenia, że strona publiczna i cel dev dotyczą tego samego elementu.",
      technical_reason: "Brakuje evidence-bound relacji source do targetu."
    },
    object_readiness: {
      status: "review_required",
      label: "Obiekt częściowo rozpoznany",
      reason: "Brakuje potwierdzonego obiektu WordPress i celu dev, w którym można przygotować zmianę.",
      technical_reason: "Brakuje dokładnego obiektu i targetu dev.",
      blocker_codes: ["object_identity_unverified"]
    },
    decision_disposition: {
      status: "proposed",
      proposed_disposition: "refresh_or_merge",
      label: "Odśwież lub scal istniejącą stronę",
      reason: "To rekomendowany kierunek; ostateczną decyzję podejmuje człowiek.",
      technical_reason: "To istniejący publiczny adres."
    },
    service: {
      label: "BDO i sprawozdawczość środowiskowa",
      reason: "Usługa pochodzi z dopasowanej karty Service Profile."
    },
    evidence_readiness: {
      status: "refresh_required",
      label: "Dowody wymagają odświeżenia",
      reason: "GSC jest nieświeże dla tej decyzji.",
      technical_reason: "GSC jest nieświeże dla tej decyzji.",
      blocker_codes: ["connector:google_search_console"]
    },
    delivery_capability: {
      capability: "create_draft_only",
      request_status: "blocked",
      label: "Szkic dev wymaga potwierdzenia targetu",
      reason: "Przekazanie szkicu pozostaje zablokowane, dopóki nie potwierdzimy celu dev i nie przejdziemy wymaganych kontroli.",
      technical_reason: "Brakuje targetu; ActionObject i accepted revision pozostają zablokowane."
    },
    measurement_target: {
      status: "review_required",
      label: "Pomiar wymaga sprawdzenia",
      public_url: "https://ekologus.pl/bdo/",
      reason: "Brakuje exact measurement bindingu.",
      technical_reason: "Brakuje exact measurement bindingu.",
      source_connectors: ["google_search_console"]
    },
    applicable_signals: [
      {
        source_connector: "google_search_console",
        label: "Wyświetlenia GSC",
        value: 181,
        freshness_state: "stale",
        evidence_ids: ["ev_gsc_bdo"]
      }
    ],
    next_safe_action: {
      kind: "refresh_connector",
      label: "Odśwież GSC",
      reason: "GSC jest nieświeże dla tej decyzji.",
      connector_id: "google_search_console"
    },
    secondary_disclosures: [{
      id: "delivery-boundary",
      label: "Granica delivery",
      summary: "WILQ nie aktualizuje istniejącej strony bez review."
    }],
    legacy_aliases: [{ kind: "requested_work_item", value: "content_work_item_bdo" }]
  };
}

function contentDocumentWorkspace(): ContentDocumentWorkspace {
  const revision = savedFullDraftRevision();
  return {
    response_type: "content_document_workspace",
    contract_version: "content_document_workspace_v1",
    work_item_id: revision.work_item_id,
    work_kind: "refresh_existing",
    service_label: "BDO i sprawozdawczość środowiskowa",
    source_snapshot: {
      status: "available",
      title: "Aktualny materiał BDO",
      url: "https://ekologus.pl/bdo/",
      extraction_method: "wordpress_rest.content",
      lead: "Aktualna strona wyjaśnia podstawowe obowiązki BDO.",
      content_excerpt: "Aktualny fragment materiału źródłowego BDO.",
      ordered_sections: [
        { heading: "Kto powinien sprawdzić obowiązek wpisu?", excerpt: "Aktualna odpowiedź." },
        { heading: "Jak prowadzić ewidencję odpadów?", excerpt: "Aktualny opis ewidencji." }
      ],
      faq_status: "not_observed",
      cta_status: "not_observed",
      reason: "WILQ odczytał aktualny publiczny materiał tej strony.",
      caveats: [],
      evidence_ids: ["ev_wp_bdo"]
    },
    canonical_document: {
      status: "unreviewed",
      revision_id: revision.revision_id,
      content_digest: revision.content_digest,
      review_state: "unreviewed",
      label: "Nowa wersja czeka na review",
      reason: "Istnieje dokładna rewizja dokumentu, ale nie ma jeszcze decyzji człowieka.",
      preview: {
        title: revision.title,
        h1: revision.page_assets?.h1 ?? null,
        lead: revision.page_assets?.lead ?? null,
        sections: revision.sections.map((section) => ({
          section_id: section.section_id,
          heading: section.heading,
          body_markdown: section.body_markdown,
          content_html: section.content_html
        })),
        faq_count: revision.faq.length,
        cta_count: revision.cta_blocks.length
      }
    },
    comparison: {
      status: "available",
      reason: "Porównanie pokazuje tylko jawne relacje między nagłówkami.",
      items: [{
        status: "source_only",
        source_heading: "Kto powinien sprawdzić obowiązek wpisu?",
        source_excerpt: "Aktualna odpowiedź.",
        document_section_id: null,
        document_heading: null,
        document_excerpt: null,
        reason: "Brak bezpośrednio rozpoznanego odpowiednika."
      }]
    },
    next_action: {
      kind: "open_review",
      label: "Przejdź do review",
      reason: "Dokument istnieje i czeka na decyzję człowieka."
    },
    secondary_disclosures: []
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
        source_fact_ids: [],
        source_material_ids: [],
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
        summary: "GSC pokazuje popyt na temat BDO.",
        source_fact_ids: [],
        source_material_ids: []
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
      source_fact_ids: ["ekologus_public_bdo_faq_2026_07_01"],
      source_material_ids: [],
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
  candidate = contentQueueResponse().candidates[0],
  item = workItem(),
  review = null,
  handoff = null,
  workspace = revisionWorkspace(),
  planning = planningWorkspace(),
  currentStepId = "draft",
  steps = operatorSteps()
}: {
  candidate?: ContentWorkItemQueueResponse["candidates"][number];
  item?: ContentWorkItem;
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
    candidate,
    service_profile_context: serviceProfileContext(),
    claim_ledger: claimLedger(),
    preflight: {
      item,
      inventory_resolution: inventoryResolution(),
      preflight_verdict: preflightVerdict("plan_allowed")
    },
    sales_brief: {
      item,
      inventory_resolution: inventoryResolution(),
      preflight_verdict: preflightVerdict("brief_allowed"),
      sales_brief_result: { brief: salesBrief(), blockers: [] }
    },
    draft_package: {
      item,
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
  generated = false,
  staleScopeDecision = false
}: {
  scopeCurrent?: boolean;
  sectionMapCurrent?: boolean;
  generated?: boolean;
  staleScopeDecision?: boolean;
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
      evidence_ids: section.evidence_ids,
      source_material_ids: [],
      knowledge_card_ids: []
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
    source_connectors: ["google_search_console", "wordpress_ekologus"],
    source_material_ids: [],
    knowledge_card_ids: []
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
    scope_decision: scopeCurrent || staleScopeDecision ? decision("scope") : null,
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
      claim_ids: [],
      source_material_ids: [],
      knowledge_card_ids: []
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
    source_material_ids: [],
    knowledge_card_ids: [],
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
      source_material_ids: [],
      knowledge_card_ids: [],
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
        claim_ids: [],
        source_material_ids: [],
        knowledge_card_ids: []
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
      "WILQ dopasował kartę BDO, ale Service Profile nie ma jeszcze zatwierdzenia do tworzenia finalnych treści.",
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
    source_fact_ids: ["ekologus_public_bdo_faq_2026_07_01"],
    source_material_ids: [],
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
    authoring_mode: "the_content" as const,
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
          claim_ids: ["claim_general_bdo"],
          source_material_ids: [],
          knowledge_card_ids: []
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
        authoring_mode: "the_content",
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
    profile_version: "wordpress_authoring_profile_v2",
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
      item_count: 1,
      items: [
        {
          post_id: "2",
          content_type: "page",
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

function knowledgeReadiness() {
  return {
    status: "ready" as const,
    total_count: 15,
    imported_count: 15,
    import_pending_count: 0,
    excerpt_review_required_count: 0,
    ready_for_generation: true,
    blocker: null,
    next_step: "Korpus jest gotowy."
  };
}
