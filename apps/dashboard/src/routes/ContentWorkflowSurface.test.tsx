import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  getContentWorkItemInitialDraft,
  getContentWorkItemPlanningProposal,
  getContentRegulatorySourceFactProposal,
  getContentWorkItemEditorialIntegrity,
  getContentWorkItemSemanticReview,
  getContentWorkItemRevisionHtmlPackage,
  getContentRevisionTargetMapping,
  getContentRevisionTargetDraftPreview,
  getContentRevisionPublicDeployment,
  postContentRevisionTargetDraftAction,
  postContentRevisionTargetMappingConfirmation,
  postContentRevisionPublicDeployment,
  postContentWorkItemMeasurementWindow,
  getContentSelectedWorkspace,
  getContentInventoryCatalog,
  getContentOperatorContext,
  getContentDiagnostics,
  postContentWorkItemInitialDraft,
  postContentRegulatorySourceFactProposalReview,
  postContentWorkItemOfficialSourceLineageRebase,
  postContentWorkItemRevisionRepairProposal,
  saveContentWorkItemDraftRevisionReview,
  type ActionObject,
  type ContentDraftRevision,
  type ContentDraftRevisionReview,
  type ContentInitialDraftResponse,
  type ContentDocumentWorkspace,
  type ContentSelectedWorkspace,
  type ContentInventoryCatalogResponse,
  type ContentTargetMappingPreview,
  type ContentTargetDraftPreview,
} from "../lib/api";
import { App, createWilqQueryClient, createWilqRouter } from "./App";
vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return {
    ...actual,
    getContentWorkItemInitialDraft: vi.fn(),
    getContentWorkItemPlanningProposal: vi.fn(),
    getContentRegulatorySourceFactProposal: vi.fn(),
    getContentWorkItemEditorialIntegrity: vi.fn(),
    getContentWorkItemSemanticReview: vi.fn(),
    getContentWorkItemRevisionHtmlPackage: vi.fn(),
    getContentRevisionTargetMapping: vi.fn(),
    getContentRevisionTargetDraftPreview: vi.fn(),
    getContentRevisionPublicDeployment: vi.fn(),
    postContentRevisionTargetMappingConfirmation: vi.fn(),
    postContentRevisionTargetDraftAction: vi.fn(),
    postContentRevisionPublicDeployment: vi.fn(),
    postContentWorkItemMeasurementWindow: vi.fn(),
    getContentSelectedWorkspace: vi.fn(),
    getContentInventoryCatalog: vi.fn(),
    getContentOperatorContext: vi.fn(),
    getContentDiagnostics: vi.fn(),
    postContentWorkItemInitialDraft: vi.fn(),
    postContentRegulatorySourceFactProposalReview: vi.fn(),
    postContentWorkItemOfficialSourceLineageRebase: vi.fn(),
    postContentWorkItemRevisionRepairProposal: vi.fn(),
    saveContentWorkItemDraftRevisionReview: vi.fn(),
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
    vi.mocked(getContentWorkItemInitialDraft).mockResolvedValue(initialDraftResponse());
    vi.mocked(getContentWorkItemPlanningProposal).mockResolvedValue({
      status: "not_generated",
      work_item_id: "content_work_item_bdo",
      proposal: null,
      blockers: [],
      safe_next_step: "Przygotuj plan.",
      publish_ready: false
    } as never);
    vi.mocked(getContentRegulatorySourceFactProposal).mockResolvedValue({
      status: "not_generated",
      proposal: null,
      reason: "Nie ma jeszcze propozycji do review.",
      safe_next_step: "Przygotuj propozycję do review."
    } as never);
    vi.mocked(getContentSelectedWorkspace).mockResolvedValue(selectedWorkspace());
    vi.mocked(getContentInventoryCatalog).mockResolvedValue(contentInventoryCatalog());
    vi.mocked(getContentDiagnostics).mockResolvedValue({
      marketer_decision: null
    } as never);
    vi.mocked(getContentRevisionPublicDeployment).mockResolvedValue({
      deployment: null,
      publication_observations: [],
      safe_next_step: "Potwierdź publiczne wdrożenie na podstawie odczytu WordPressa."
    } as never);
    vi.mocked(postContentWorkItemMeasurementWindow).mockResolvedValue({
      measurement_window_result: { window: null, blockers: [] }
    } as never);
    vi.mocked(postContentWorkItemInitialDraft).mockResolvedValue(initialDraftResponse());
    vi.mocked(postContentWorkItemOfficialSourceLineageRebase).mockResolvedValue({
      status: "created",
      revision: savedFullDraftRevision(),
      workspace: {} as never
    });
    vi.mocked(postContentWorkItemRevisionRepairProposal).mockResolvedValue({
      status: "created",
      run_id: "codex_repair_1",
      work_item_id: "content_work_item_bdo",
      base_revision_id: "content_revision_bdo_1",
      selected_section_headings: ["Kto powinien sprawdzić obowiązek wpisu?"],
      selected_cta_ids: [],
      revision: savedFullDraftRevision(),
      quality_review: { verdict: "reviewable" },
      quality_review_scope: "persisted_selected_sections_and_declared_lineage",
      semantic_review_required: true,
      runtime: { status: "completed", thread_id: null, turn_id: null, event_methods: [], item_types: [], external_call_attempted: false },
      evidence_ids: [],
      source_connectors: [],
      blockers: [],
      safe_next_step: "Sprawdź nową wersję.",
      publish_ready: false
    } as never);
    const revision = savedDraftRevision();
    const review = savedDraftRevisionReview(revision);
    vi.mocked(saveContentWorkItemDraftRevisionReview).mockResolvedValue({
      status: "recorded",
      review,
      workspace: {} as never
    } as never);
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.unstubAllGlobals();
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
    noDocument.document_lineage = {
      status: "not_recorded",
      source_material_ids: [],
      knowledge_cards: [],
      unresolved_knowledge_card_ids: [],
      reason: "Nie ma jeszcze zapisanej rewizji, więc WILQ nie może wskazać materiałów przypisanych do dokumentu."
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
    vi.mocked(getContentSelectedWorkspace).mockResolvedValue(selectedWorkspace(noDocument));

    const client = createWilqQueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo&text=1", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    expect(await screen.findByTestId("content-text-workspace")).toBeInTheDocument();
    expect(screen.getByTestId("content-document-state")).toHaveTextContent("Nowa wersja nie została jeszcze przygotowana");
    expect(screen.getByText(/Nie ma jeszcze zapisanej wersji dokumentu/)).toBeInTheDocument();
    expect(screen.queryByTestId("content-official-sources")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Nowa wersja" }));
    expect(screen.getByRole("heading", { name: "Nowa wersja nie została jeszcze przygotowana" })).toBeInTheDocument();
  });

  it("opens an existing prepared text before the source so the marketer can review the actual deliverable", async () => {
    const revision = savedFullDraftRevision();
    vi.mocked(getContentSelectedWorkspace).mockResolvedValue(
      selectedWorkspace(contentDocumentWorkspace(revision))
    );

    const client = createWilqQueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <App
        appRouter={createWilqRouter({
          initialPath: "/content-workflow?work_item_id=content_work_item_bdo&text=1",
          defaultPendingMinMs: 0
        })}
        client={client}
      />
    );

    expect(await screen.findByText("Pełna odpowiedź sekcji 1 oparta na planie i dowodach.")).toBeInTheDocument();
    expect(screen.queryByTestId("content-source-snapshot")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Porównanie" })).toBeInTheDocument();
    expect(screen.queryByTestId("content-official-sources")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Obecna strona" }));
    expect(await screen.findByTestId("content-source-snapshot")).toBeInTheDocument();
  });

  it("fails closed for blank official-source data on the exact revision", async () => {
    const revision = {
      ...savedFullDraftRevision(),
      official_source_references: [{
        ...savedFullDraftRevision().official_source_references[0]!,
        source_title: "   "
      }]
    };
    vi.mocked(getContentSelectedWorkspace).mockResolvedValue(selectedWorkspace(contentDocumentWorkspace(revision)));

    const client = createWilqQueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<App appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo&view=review", defaultPendingMinMs: 0 })} client={client} />);

    expect(await screen.findByText("Pełna odpowiedź sekcji 1 oparta na planie i dowodach.")).toBeInTheDocument();
    expect(screen.queryByTestId("content-official-sources")).not.toBeInTheDocument();
  });

  it("keeps official-source lineage changes out of the immutable document canvas", async () => {
    const revision = { ...savedFullDraftRevision(), official_source_references: [] };
    vi.mocked(getContentSelectedWorkspace).mockResolvedValue(
      selectedWorkspace(contentDocumentWorkspace(revision))
    );
    const client = createWilqQueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<App appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo&text=1", defaultPendingMinMs: 0 })} client={client} />);

    await screen.findByText("Pełna odpowiedź sekcji 1 oparta na planie i dowodach.");
    expect(screen.queryByRole("button", { name: "Uzupełnij źródła urzędowe" })).not.toBeInTheDocument();
    expect(postContentWorkItemOfficialSourceLineageRebase).not.toHaveBeenCalled();
  });

  it("does not inject a regulatory source candidate into the exact document workspace", async () => {
    const workspace = contentDocumentWorkspace();
    workspace.regulatory_review_candidates = [{
      candidate_id: "bdo_sanctions_2026_08_02_r3",
      source_url: "https://bdo.mos.gov.pl/baza-wiedzy/sankcje/",
      source_title: "BDO: sankcje za naruszenia obowiązków",
      observed_on: "2026-08-02",
      requirement_ids: ["bdo_risks_and_sanctions"],
      requirement_labels: ["Ryzyka i sankcje"],
      review_status: "review_required",
      safe_next_step: "Sprawdź propozycję z materiałem urzędowym przed decyzją."
    }];
    vi.mocked(getContentSelectedWorkspace).mockResolvedValue(selectedWorkspace(workspace));
    vi.mocked(getContentRegulatorySourceFactProposal).mockResolvedValue({
      status: "ready",
      proposal: {
        proposal_id: "regulatory_source_fact_proposal_sanctions",
        candidate_id: "bdo_sanctions_2026_08_02_r3",
        profile_id: "bdo",
        profile_version: "2026-08",
        source_url: "https://bdo.mos.gov.pl/baza-wiedzy/sankcje/",
        source_title: "BDO: sankcje za naruszenia obowiązków",
        source_snapshot_id: "regulatory_snapshot_sanctions",
        source_snapshot_digest: "d".repeat(64),
        observed_on: "2026-08-02",
        proposed_fact: "Naruszenia obowiązków BDO mogą prowadzić do sankcji wskazanych w materiale urzędowym.",
        covered_requirement_ids: ["bdo_risks_and_sanctions"],
        codex_run_id: "codex_regulatory_source_fact_sanctions",
        status: "ready",
        human_review_required: true,
        created_at: "2026-08-02T12:00:00Z"
      },
      reason: "Propozycja wymaga decyzji człowieka.",
      safe_next_step: "Porównaj ją z materiałem urzędowym."
    } as never);

    const client = createWilqQueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<App appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo&text=1", defaultPendingMinMs: 0 })} client={client} />);

    await screen.findByTestId("content-text-workspace");
    expect(screen.queryByText("Naruszenia obowiązków BDO mogą prowadzić do sankcji wskazanych w materiale urzędowym.")).not.toBeInTheDocument();
    expect(getContentRegulatorySourceFactProposal).not.toHaveBeenCalled();
    expect(postContentRegulatorySourceFactProposalReview).not.toHaveBeenCalled();
  });

  it("opens a newly saved exact revision instead of leaving the marketer on the old source", async () => {
    const withoutDocument = contentDocumentWorkspace();
    withoutDocument.canonical_document = {
      status: "not_created",
      revision_id: null,
      content_digest: null,
      review_state: "unreviewed",
      label: "Nowa wersja nie została jeszcze przygotowana",
      reason: "Nie ma jeszcze zapisanej wersji dokumentu.",
      preview: null
    };
    const revision = savedFullDraftRevision();
    vi.mocked(getContentSelectedWorkspace)
      .mockResolvedValueOnce(selectedWorkspace(withoutDocument))
      .mockResolvedValueOnce(selectedWorkspace(contentDocumentWorkspace(revision)));

    const client = createWilqQueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <App
        appRouter={createWilqRouter({
          initialPath: "/content-workflow?work_item_id=content_work_item_bdo&text=1",
          defaultPendingMinMs: 0
        })}
        client={client}
      />
    );

    expect(await screen.findByTestId("content-source-snapshot")).toBeInTheDocument();
    await client.refetchQueries({
      queryKey: ["content-workflow", "work-item", "content_work_item_bdo", "selected-workspace"]
    });

    expect(await screen.findByText("Pełna odpowiedź sekcji 1 oparta na planie i dowodach.")).toBeInTheDocument();
    expect(screen.queryByTestId("content-source-snapshot")).not.toBeInTheDocument();
  });

  it.each(["review=1", "text=1&review=1"])(
    "opens the exact review route when navigation queue reads reject (%s)",
    async (reviewSearch) => {
      const revision = savedFullDraftRevision();
      vi.mocked(getContentSelectedWorkspace).mockResolvedValue(selectedWorkspace(contentDocumentWorkspace(revision)));

      render(
        <App
          appRouter={createWilqRouter({
            initialPath: `/content-workflow?work_item_id=content_work_item_bdo&${reviewSearch}`,
            defaultPendingMinMs: 0
          })}
          client={createWilqQueryClient({ defaultOptions: { queries: { retry: false } } })}
        />
      );

      expect(await screen.findByTestId("content-review-workspace")).toBeInTheDocument();
      expect(screen.queryByText("Nie udało się odczytać aktualnego workflow.")).not.toBeInTheDocument();
      expect(getContentSelectedWorkspace).toHaveBeenCalledWith("content_work_item_bdo");
      expect(getContentWorkItemInitialDraft).not.toHaveBeenCalled();
      expect(getContentDiagnostics).not.toHaveBeenCalled();
    }
  );

  it("opens and emits the canonical work-item path", async () => {
    const revision = savedFullDraftRevision();
    vi.mocked(getContentSelectedWorkspace).mockResolvedValue(selectedWorkspace(contentDocumentWorkspace(revision)));
    const appRouter = createWilqRouter({
      initialPath: "/content-workflow/content_work_item_bdo",
      defaultPendingMinMs: 0
    });

    render(<App appRouter={appRouter} client={createWilqQueryClient({ defaultOptions: { queries: { retry: false } } })} />);

    expect(await screen.findByTestId("content-text-workspace")).toBeInTheDocument();
    expect(getContentSelectedWorkspace).toHaveBeenCalledWith("content_work_item_bdo");
    expect(getContentWorkItemPlanningProposal).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: /przejdź do review/i }));
    await waitFor(() => expect(appRouter.state.location.pathname).toBe("/content-workflow/content_work_item_bdo"));
    expect(appRouter.state.location.search.view).toBe("review");
  });

  it("keeps an exact missing review route separate from a warm catalogue entry", async () => {
    vi.mocked(getContentSelectedWorkspace).mockRejectedValue(new Error("Nie znaleziono strony"));
    const client = createWilqQueryClient({ defaultOptions: { queries: { retry: false } } });
    client.setQueryData(["content-workflow", "queue", "catalog"], {
      candidates: [{ work_item_id: "content_work_item_bdo" }]
    });

    render(
      <App
        appRouter={createWilqRouter({
          initialPath: "/content-workflow?work_item_id=content_work_item_bdo&review=1",
          defaultPendingMinMs: 0
        })}
        client={client}
      />
    );

    expect(await screen.findByTestId("content-document-workspace-error")).toBeInTheDocument();
    expect(getContentSelectedWorkspace).toHaveBeenCalledWith("content_work_item_bdo");
    expect(screen.queryByTestId("content-review-workspace")).not.toBeInTheDocument();
  });

  it("shows target mapping as an explicit, read-only detail without loading it automatically", async () => {
    const workspace = approvedDocumentWorkspace();
    vi.mocked(getContentSelectedWorkspace).mockResolvedValue(selectedWorkspace(workspace));
    vi.mocked(getContentRevisionTargetMapping).mockResolvedValue(
      contentTargetMappingPreview()
    );

    const client = createWilqQueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <App
        appRouter={createWilqRouter({
          initialPath: "/content-workflow?work_item_id=content_work_item_bdo&text=1",
          defaultPendingMinMs: 0
        })}
        client={client}
      />
    );

    expect(await screen.findByTestId("content-text-workspace")).toBeInTheDocument();
    expect(screen.getByText("Przypisanie dokumentu do dev", { exact: true })).toBeInTheDocument();
    expect(postContentRevisionTargetMappingConfirmation).not.toHaveBeenCalled();
    expect(getContentRevisionTargetMapping).not.toHaveBeenCalled();
  });

  it("does not offer a mapping confirmation from the text workspace", async () => {
    const workspace = approvedDocumentWorkspace();
    const preview = contentTargetMappingPreview();
    vi.mocked(getContentSelectedWorkspace).mockResolvedValue(selectedWorkspace(workspace));
    vi.mocked(getContentRevisionTargetMapping).mockResolvedValue(preview);
    vi.mocked(postContentRevisionTargetMappingConfirmation).mockResolvedValue({
      status: "created",
      confirmation: {
        confirmation_id: "content_target_mapping_confirmation_1",
        confirmation_number: 1,
        work_item_id: workspace.work_item_id,
        revision: preview.revision,
        target_contract_digest: "b".repeat(64),
        binding_digest: "c".repeat(64),
        selections: [{
          component_id: "section:section_bdo",
          layout_name: "text_section",
          field_bindings: [
            { source_field: "heading", target_field: "heading" },
            { source_field: "content_html", target_field: "content_html" }
          ]
        }],
        confirmed_by: "Marta Kowalska",
        confirmation_digest: "d".repeat(64),
        created_at: "2026-07-25T10:00:00Z"
      }
    });

    const client = createWilqQueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <App
        appRouter={createWilqRouter({
          initialPath: "/content-workflow?work_item_id=content_work_item_bdo&text=1",
          defaultPendingMinMs: 0
        })}
        client={client}
      />
    );

    expect(await screen.findByTestId("content-text-workspace")).toBeInTheDocument();
    expect(screen.queryByTestId("target-mapping-confirmation")).not.toBeInTheDocument();
    expect(postContentRevisionTargetMappingConfirmation).not.toHaveBeenCalled();
  });

  it("keeps public-deployment confirmation out of the text workspace", async () => {
    const workspace = approvedDocumentWorkspace();
    vi.mocked(getContentSelectedWorkspace).mockResolvedValue(selectedWorkspace(workspace));
    vi.mocked(getContentRevisionPublicDeployment).mockResolvedValue({
      deployment: null,
      publication_observations: [{
        wordpress_post_id: "1353",
        publication_evidence_id: "ev_public_bdo",
        publication_source_connector: "wordpress_ekologus",
        public_url: "https://www.ekologus.pl/bdo/",
        observed_at: "2026-07-26T09:00:00Z"
      }],
      safe_next_step: "Potwierdź publiczne wdrożenie na podstawie odczytu WordPressa."
    } as never);
    vi.mocked(postContentRevisionPublicDeployment).mockResolvedValue({
      deployment: {
        deployment_id: "content_public_deployment_bdo",
        work_item_id: workspace.work_item_id,
        revision_id: workspace.canonical_document.revision_id,
        revision_digest: workspace.canonical_document.content_digest,
        public_url: "https://www.ekologus.pl/bdo/",
        wordpress_post_id: "1353",
        publication_evidence_id: "ev_public_bdo",
        publication_source_connector: "wordpress_ekologus",
        observed_at: "2026-07-26T09:00:00Z",
        confirmed_by: "Marta Kowalska",
        confirmed_at: "2026-07-26T10:00:00Z"
      }
    } as never);

    render(
      <App
        appRouter={createWilqRouter({
          initialPath: "/content-workflow?work_item_id=content_work_item_bdo&text=1",
          defaultPendingMinMs: 0
        })}
        client={createWilqQueryClient({ defaultOptions: { queries: { retry: false } } })}
      />
    );

    await screen.findByTestId("content-text-workspace");
    expect(screen.queryByText("Potwierdzenie publicznego wdrożenia", { exact: true })).not.toBeInTheDocument();
    expect(postContentRevisionPublicDeployment).not.toHaveBeenCalled();
  });

  it("keeps deployment measurement out of the text workspace", async () => {
    const workspace = approvedDocumentWorkspace();
    vi.mocked(getContentSelectedWorkspace).mockResolvedValue(selectedWorkspace(workspace));
    vi.mocked(getContentRevisionPublicDeployment).mockResolvedValue({
      deployment: {
        deployment_id: "content_public_deployment_bdo",
        work_item_id: workspace.work_item_id,
        revision_id: workspace.canonical_document.revision_id,
        revision_digest: workspace.canonical_document.content_digest,
        public_url: "https://www.ekologus.pl/bdo/",
        wordpress_post_id: "1353",
        publication_evidence_id: "ev_public_bdo",
        publication_source_connector: "wordpress_ekologus",
        observed_at: "2026-07-26T09:00:00Z",
        confirmed_by: "Marta Kowalska",
        confirmed_at: "2026-07-26T10:00:00Z"
      },
      publication_observations: [],
      measurement_window: null,
      measurement_outcome: null,
      learning_proposal: null,
      outcome_allowed: false,
      safe_next_step: "Przygotuj okno pomiaru dla tego potwierdzonego wdrożenia."
    } as never);

    render(
      <App
        appRouter={createWilqRouter({
          initialPath: "/content-workflow?work_item_id=content_work_item_bdo&text=1",
          defaultPendingMinMs: 0
        })}
        client={createWilqQueryClient({ defaultOptions: { queries: { retry: false } } })}
      />
    );

    await screen.findByTestId("content-text-workspace");
    expect(screen.queryByText("Potwierdzenie publicznego wdrożenia", { exact: true })).not.toBeInTheDocument();
    expect(postContentWorkItemMeasurementWindow).not.toHaveBeenCalled();
  });

  it("offers the approved document package without loading it automatically", async () => {
    const workspace = approvedDocumentWorkspace();
    vi.mocked(getContentSelectedWorkspace).mockResolvedValue(selectedWorkspace(workspace));

    const client = createWilqQueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <App
        appRouter={createWilqRouter({
          initialPath: "/content-workflow?work_item_id=content_work_item_bdo&text=1",
          defaultPendingMinMs: 0
        })}
        client={client}
      />
    );

    expect(await screen.findByTestId("content-text-workspace")).toBeInTheDocument();
    expect(screen.getByTestId("content-approved-html-package")).toBeInTheDocument();
    expect(getContentWorkItemRevisionHtmlPackage).not.toHaveBeenCalled();
  });

  it("does not prepare a dev-draft action until the marketer opens its explicit preview", async () => {
    const workspace = approvedDocumentWorkspace();
    const preview = contentTargetDraftPreview();
    vi.mocked(getContentSelectedWorkspace).mockResolvedValue(selectedWorkspace(workspace));
    vi.mocked(getContentRevisionTargetDraftPreview).mockResolvedValue(preview);
    vi.mocked(postContentRevisionTargetDraftAction).mockResolvedValue({
      ...wordpressDraftAction(),
      id: "act_content_dev_draft_1"
    });

    const client = createWilqQueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <App
        appRouter={createWilqRouter({
          initialPath: "/content-workflow?work_item_id=content_work_item_bdo&text=1",
          defaultPendingMinMs: 0
        })}
        client={client}
      />
    );

    expect(await screen.findByTestId("content-text-workspace")).toBeInTheDocument();
    expect(screen.getByText("Podgląd danych do szkicu na dev", { exact: true })).toBeInTheDocument();
    expect(postContentRevisionTargetDraftAction).not.toHaveBeenCalled();
  });

  it("does not load target mapping details until the marketer opens them", async () => {
    const workspace = approvedDocumentWorkspace();
    vi.mocked(getContentSelectedWorkspace).mockResolvedValue(selectedWorkspace(workspace));
    vi.mocked(getContentRevisionTargetMapping).mockResolvedValue(
      contentTargetMappingPreview({ postType: "page", status: "blocked" })
    );

    const client = createWilqQueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <App
        appRouter={createWilqRouter({
          initialPath: "/content-workflow?work_item_id=content_work_item_bdo&text=1",
          defaultPendingMinMs: 0
        })}
        client={client}
      />
    );

    expect(await screen.findByTestId("content-text-workspace")).toBeInTheDocument();
    expect(screen.getByText("Przypisanie dokumentu do dev", { exact: true })).toBeInTheDocument();
    expect(getContentRevisionTargetMapping).not.toHaveBeenCalled();
  });

  it("records human review for the exact Text revision without opening a content write path", async () => {
    const revision = savedFullDraftRevision();
    vi.mocked(getContentSelectedWorkspace).mockResolvedValue(selectedWorkspace(contentDocumentWorkspace(revision)));

    const client = createWilqQueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo&text=1&review=1", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    expect(await screen.findByTestId("content-review-workspace")).toBeInTheDocument();
    expect(screen.getByTestId("content-full-page-preview")).toBeInTheDocument();
    expect(screen.getByText("Szczegóły tej wersji")).toBeInTheDocument();
    expect(screen.getByTestId("content-document-lineage")).toHaveTextContent("Pochodzenie źródeł dokumentu");
    expect(screen.getByText("Sprawdź nową wersję")).toBeInTheDocument();
    expect(screen.queryByLabelText("Stan pipeline’u")).not.toBeInTheDocument();
    expect(screen.queryByText(/zatwierdź plan/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/0 dokładnie dopasowanych sygnałów zapytań/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Wróć do edytora/)).not.toBeInTheDocument();
    const save = screen.getByRole("button", { name: "Zatwierdź tekst" });
    expect(save).toBeEnabled();
    fireEvent.click(save);

    await waitFor(() => expect(saveContentWorkItemDraftRevisionReview).toHaveBeenCalledTimes(1));
    expect(vi.mocked(saveContentWorkItemDraftRevisionReview).mock.calls[0]).toEqual([
      expect.objectContaining({
        expected_revision_digest: revision.content_digest,
        reviewed_by: "wilku",
        decision: "approved",
        checked_items: [
          "Tekst sprawdzony przed zatwierdzeniem.",
          "Dowody tej rewizji sprawdzone przed zatwierdzeniem."
        ],
        evidence_ids: uniqueTestEvidence(revision)
      }),
      revision.work_item_id,
      revision.revision_id
    ]);
    expect(postContentWorkItemInitialDraft).not.toHaveBeenCalled();
  });

  it("downloads only the exact approved revision as a read-only HTML package", async () => {
    const revision = savedFullDraftRevision();
    const review = savedDraftRevisionReview(revision, "approved");
    vi.mocked(getContentSelectedWorkspace).mockResolvedValue(selectedWorkspace(contentDocumentWorkspace(revision, review)));
    vi.mocked(getContentWorkItemRevisionHtmlPackage).mockResolvedValue({
      manifest: {
        work_item_id: revision.work_item_id,
        revision_id: revision.revision_id,
        content_digest: revision.content_digest,
        final_canonical_url: revision.final_canonical_url ?? "https://ekologus.pl/bdo/",
        evidence_ids: uniqueTestEvidence(revision),
        source_material_ids: revision.source_material_ids,
        knowledge_card_ids: revision.knowledge_card_ids,
        official_source_references: revision.official_source_references,
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
        appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo&text=1&review=1", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    expect(await screen.findByTestId("content-approved-html-package")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Pobierz paczkę dokumentu" }));

    await waitFor(() => expect(getContentWorkItemRevisionHtmlPackage).toHaveBeenCalledWith(revision.work_item_id, revision.revision_id));
    expect(createObjectURL).toHaveBeenCalledTimes(1);
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:approved-revision");
    expect(postContentWorkItemInitialDraft).not.toHaveBeenCalled();
    anchorClick.mockRestore();
  });

  it("reads editorial integrity for the exact revision without starting a revision or review mutation", async () => {
    const revision = { ...savedFullDraftRevision(), base_revision_id: "content_revision_base" };
    vi.mocked(getContentSelectedWorkspace).mockResolvedValue(selectedWorkspace(contentDocumentWorkspace(revision)));
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
    render(<App appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo&text=1&review=1", defaultPendingMinMs: 0 })} client={client} />);

    fireEvent.click(await screen.findByRole("button", { name: "Sprawdź zmiany względem wersji bazowej" }));
    await waitFor(() => expect(getContentWorkItemEditorialIntegrity).toHaveBeenCalledWith(revision.work_item_id, revision.revision_id));
    expect(await screen.findByText("Twarda integralność zachowana")).toBeInTheDocument();
    expect(screen.getByText(/Porównanie: R8 → R10 → R11/)).toBeInTheDocument();
    expect(screen.getByText(/Human review tej rewizji: zatwierdzone/)).toBeInTheDocument();
    expect(postContentWorkItemInitialDraft).not.toHaveBeenCalled();
    expect(saveContentWorkItemDraftRevisionReview).not.toHaveBeenCalled();
  });

  it("reads advisory semantic guidance for the exact revision without changing the text or human review", async () => {
    const revision = savedFullDraftRevision();
    vi.mocked(getContentSelectedWorkspace).mockResolvedValue(selectedWorkspace(contentDocumentWorkspace(revision)));
    vi.mocked(getContentWorkItemSemanticReview).mockResolvedValue({
      status: "ready",
      work_item_id: revision.work_item_id,
      revision_id: revision.revision_id,
      revision_digest: revision.content_digest,
      run_id: "codex_semantic_review_1",
      runtime: {
        status: "completed",
        run_id: "codex_semantic_review_1",
        thread_id: null,
        turn_id: null,
        event_methods: [],
        item_types: [],
        external_call_attempted: false
      },
      review: {
        review_id: "content_semantic_review_1",
        work_item_id: revision.work_item_id,
        revision_id: revision.revision_id,
        revision_digest: revision.content_digest,
        criteria_version: "wilq_semantic_content_review_v1",
        codex_run_id: "codex_semantic_review_1",
        status: "needs_changes",
        dimensions: [],
        findings: [{ finding_id: "finding_1", dimension: "conversion_clarity", severity: "medium", label: "Kolejny krok wymaga doprecyzowania", reason: "Czytelnik nie dostaje jasnego następnego kroku.", instruction: "Dodaj konkretne wezwanie do kontaktu.", affected_targets: ["section_1"], evidence_ids: [] }],
        evidence_ids: [],
        source_connectors: [],
        requested_by: "wilku",
        created_at: "2026-07-29T08:00:00Z",
        safe_next_step: "Sprawdź wskazówkę przed podjęciem decyzji.",
        publish_ready: false,
        human_review_required: true,
        action_object_created: false
      },
      blockers: [],
      safe_next_step: "Sprawdź wskazówkę przed podjęciem decyzji.",
      publish_ready: false,
      human_review_required: true,
      action_object_created: false
    } as never);

    const client = createWilqQueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<App appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo&text=1&review=1", defaultPendingMinMs: 0 })} client={client} />);

    fireEvent.click(await screen.findByRole("button", { name: "Pokaż wskazówki jakości" }));
    await waitFor(() => expect(getContentWorkItemSemanticReview).toHaveBeenCalledWith(revision.work_item_id, revision.revision_id));
    expect(await screen.findByText("Kolejny krok wymaga doprecyzowania")).toBeInTheDocument();
    expect(screen.getByText(/Dodaj konkretne wezwanie do kontaktu/)).toBeInTheDocument();
    expect(postContentWorkItemInitialDraft).not.toHaveBeenCalled();
    expect(saveContentWorkItemDraftRevisionReview).not.toHaveBeenCalled();
  });

  it("offers one exact repair only after the human records needs changes", async () => {
    const revision = savedFullDraftRevision();
    const review = savedDraftRevisionReview(revision, "needs_changes");
    const workspace = contentDocumentWorkspace(revision, review);
    workspace.canonical_document.status = "needs_changes";
    workspace.canonical_document.review_state = "needs_changes";
    workspace.canonical_document.label = "Tekst wymaga zmian";
    workspace.canonical_document.reason = "Marketer zapisał dokładne uwagi do tej wersji.";
    workspace.next_action = { kind: "repair_document", label: "Przygotuj poprawkę", reason: "Dokument ma zapisane uwagi." };
    vi.mocked(getContentSelectedWorkspace).mockResolvedValue(selectedWorkspace(workspace));

    const client = createWilqQueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<App appRouter={createWilqRouter({ initialPath: "/content-workflow?work_item_id=content_work_item_bdo&view=review", defaultPendingMinMs: 0 })} client={client} />);

    const repair = await screen.findByTestId("content-revision-repair");
    expect(repair).toHaveTextContent("Uwagi marketera: Ta wersja wymaga opisanych poprawek.");
    const repairButton = screen.getByRole("button", { name: "Przygotuj poprawkę" });
    await waitFor(() => expect(repairButton).toBeEnabled());
    fireEvent.click(repairButton);

    await waitFor(() => expect(postContentWorkItemRevisionRepairProposal).toHaveBeenCalledWith(
      expect.objectContaining({
        expected_base_digest: revision.content_digest,
        selected_section_ids: [revision.sections[0]?.section_id],
        selected_cta_ids: [],
        requested_by: "wilku"
      }),
      revision.work_item_id,
      revision.revision_id
    ));
    expect(postContentWorkItemInitialDraft).not.toHaveBeenCalled();
  });

});




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

function selectedWorkspace(
  workspace = contentDocumentWorkspace()
): ContentSelectedWorkspace {
  return {
    response_type: "content_selected_workspace",
    contract_version: "content_selected_workspace_v1",
    status: "ready",
    work_item_id: workspace.work_item_id,
    workspace,
    reason: "WILQ odczytał dokładny workspace wskazanej strony.",
    safe_next_step: workspace.next_action.label
  };
}

function contentDocumentWorkspace(
  revision = savedFullDraftRevision(),
  review: ReturnType<typeof savedDraftRevisionReview> | null = null
): ContentDocumentWorkspace {
  return {
    response_type: "content_document_workspace",
    contract_version: "content_document_workspace_v2",
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
      },
      revision,
      review
    },
    document_lineage: {
      status: "available",
      source_material_ids: ["ekologus_material_bdo"],
      knowledge_cards: [{
        id: "ekologus_service_bdo_reporting",
        card_type: "service",
        title: "BDO i sprawozdawczość środowiskowa",
        summary: "Zatwierdzona karta wiedzy dotycząca usługi BDO."
      }, {
        id: "ekologus_evidence_live_connector_requirement",
        card_type: "evidence_requirement",
        title: "Live evidence i source connector są wymagane",
        summary: "Techniczna kontrola źródeł."
      }],
      unresolved_knowledge_card_ids: [],
      reason: "To są materiały i karty wiedzy zapisane przy dokładnej rewizji dokumentu."
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
    regulatory_review_candidates: [],
    secondary_disclosures: []
  };
}

function approvedDocumentWorkspace(): ContentDocumentWorkspace {
  const workspace = contentDocumentWorkspace();
  const revision = workspace.canonical_document.revision!;
  workspace.canonical_document = {
    ...workspace.canonical_document,
    status: "approved",
    review_state: "approved",
    label: "Dokument zatwierdzony",
    reason: "Dokument został zatwierdzony dla dokładnej rewizji.",
    review: savedDraftRevisionReview(revision, "approved")
  };
  return workspace;
}

function contentTargetMappingPreview({
  postType = "post",
  status = "ready"
}: {
  postType?: string;
  status?: "ready" | "blocked";
} = {}): ContentTargetMappingPreview {
  const ready = status === "ready";
  return {
    response_type: "content_target_mapping_preview",
    contract_version: "content_target_mapping_preview_v1",
    work_item_id: "content_work_item_bdo",
    revision: {
      revision_id: "content_revision_bdo",
      content_digest: "a".repeat(64)
    },
    status: ready ? "ready_for_human_mapping" : "blocked",
    target: {
      target_contract: {
        environment: "dev",
        object_id: "1353",
        url: "https://ekologus.dev.proudsite.pl/bdo/",
        post_type: postType,
        post_status: "publish",
        modified: "2026-07-24T10:00:00",
        template: null,
        authority: "observation_only",
        write_authorized: false,
        authoring_surface: ready
          ? {
              kind: "acf_flexible_content",
              root_field: "content_sections",
              layouts: [{ name: "text_section", fields: ["heading", "content_html"] }]
            }
          : null
      },
      target_contract_digest: "b".repeat(64),
      observation_evidence: {
        evidence_id: "ev_wordpress_target_bdo",
        connector_id: "wordpress_ekologus",
        object_id: "1353",
        post_type: postType,
        url: "https://ekologus.dev.proudsite.pl/bdo/",
        post_status: "publish",
        modified: "2026-07-24T10:00:00",
        observed_at: "2026-07-24T10:00:01+00:00"
      }
    },
    binding_digest: ready ? "c".repeat(64) : null,
    components: [{
      component_id: "section:section_bdo",
      kind: "rich_text",
      label: "Obowiązki BDO",
      status: ready ? "human_only" : "blocked",
      reason: ready
        ? "Wymaga decyzji człowieka."
        : "Nie rozpoznano układu treści na dev.",
      target_root_field: ready ? "content_sections" : null,
      available_layouts: ready ? ["text_section"] : [],
      source_fields: ready
        ? [
            { key: "heading", label: "Nagłówek sekcji" },
            { key: "content_html", label: "Treść sekcji" }
          ]
        : []
    }],
    blockers: ready
      ? []
      : [{
          code: "authoring_surface_unknown",
          label: "Nie rozpoznano układu treści na dev",
          reason: "Nie ma potwierdzonego układu targetu.",
          next_step: "Odczytaj układ bez zgadywania pola lub layoutu."
        }],
    caveats: ["Nie przygotowano payloadu ani zapisu do WordPressa."]
  };
}

function contentTargetDraftPreview(): ContentTargetDraftPreview {
  const mapping = contentTargetMappingPreview();
  if (!mapping.target || !mapping.binding_digest) throw new Error("Missing target mapping fixture.");
  return {
    response_type: "content_target_draft_preview",
    contract_version: "content_target_draft_preview_v1",
    work_item_id: mapping.work_item_id,
    revision: mapping.revision,
    status: "ready",
    target: mapping.target,
    confirmation: {
      confirmation_id: "content_target_mapping_confirmation_1",
      confirmation_number: 1,
      work_item_id: mapping.work_item_id,
      revision: mapping.revision,
      target_contract_digest: mapping.target.target_contract_digest,
      binding_digest: mapping.binding_digest,
      selections: [{
        component_id: "section:section_bdo",
        layout_name: "text_section",
        field_bindings: [{ source_field: "content_html", target_field: "content_html" }]
      }],
      confirmed_by: "Marta Kowalska",
      confirmation_digest: "d".repeat(64),
      created_at: "2026-07-25T10:00:00Z"
    },
    root_field: "content_sections",
    components: [{
      component_id: "section:section_bdo",
      label: "Obowiązki BDO",
      layout_name: "text_section",
      fields: [{
        target_field: "content_html",
        source_field: "content_html",
        value: "<p>Sprawdź obowiązki BDO.</p>",
        value_kind: "html"
      }]
    }],
    payload_digest: "e".repeat(64),
    blockers: [],
    caveats: ["To nadal nie tworzy draftu ani nie zmienia WordPressa."]
  };
}



function savedDraftRevision(): ContentDraftRevision {
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
    document_kind: "refresh_existing",
    title: "BDO dla firm",
    sections: [
      {
        heading: "Kogo dotyczy BDO",
        body_markdown: "Zapisana treść pierwszej wersji o obowiązkach BDO.",
        query_terms: [],
        evidence_ids: ["ev_gsc_bdo"],
        claim_ids: [],
        source_material_ids: [],
        knowledge_card_ids: []
      }
    ],
    faq: [],
    cta_blocks: [],
    internal_links: [],
    official_source_references: [],
    publish_ready: false,
    created_by: "wilku",
    created_at: "2026-07-14T04:00:00Z"
  };
}

function savedFullDraftRevision(): ContentDraftRevision {
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
    official_source_references: [{
      source_fact_id: "official_source_fact_bdo",
      source_url: "https://bdo.mos.gov.pl/",
      source_title: "Baza danych o produktach i opakowaniach oraz o gospodarce odpadami",
      verified_on: "2026-07-31",
      evidence_ids: ["ev_regulatory_bdo"],
      regulatory_requirement_ids: ["bdo_registration", "bdo_reporting"]
    }],
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
      selected_cta_ids: [],
      cta_lineage: [],
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



function savedDraftRevisionReview(
  revision: ContentDraftRevision,
  decision: "approved" | "needs_changes" | "rejected" | "deferred" = "approved"
): ContentDraftRevisionReview {
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

function uniqueTestEvidence(revision: ContentDraftRevision) {
  return [
    ...new Set([
      ...revision.sections.flatMap((section) => section.evidence_ids),
      ...revision.faq.flatMap((item) => item.evidence_ids),
      ...revision.cta_blocks.flatMap((item) => item.evidence_ids),
      ...revision.internal_links.flatMap((item) => item.evidence_ids)
    ])
  ];
}
