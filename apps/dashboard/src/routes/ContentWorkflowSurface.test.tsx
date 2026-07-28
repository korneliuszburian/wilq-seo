import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  getContentWorkItemInitialDraft,
  getContentWorkItemEditorialIntegrity,
  getContentWorkItemRevisionHtmlPackage,
  getContentRevisionTargetMapping,
  getContentRevisionTargetDraftPreview,
  postContentRevisionTargetDraftAction,
  postContentRevisionTargetMappingConfirmation,
  getContentWorkItemDecisionContext,
  getContentSelectedWorkspace,
  getContentInventoryCatalog,
  getContentOperatorContext,
  getContentWorkItemQueue,
  getContentWorkItemSnapshot,
  postContentWorkItemInitialDraft,
  postContentWorkItemWordPressDraftExecution,
  saveContentWorkItemDraftRevision,
  saveContentWorkItemDraftRevisionReview,
  type ActionObject,
  type ContentInitialDraftResponse,
  type ContentDecisionContext,
  type ContentDocumentWorkspace,
  type ContentSelectedWorkspace,
  type ContentInventoryCatalogResponse,
  type ContentTargetMappingPreview,
  type ContentTargetDraftPreview,
  type ContentWorkItemQueueResponse,
  type ContentWorkItemWorkflowSnapshotResponse,
} from "../lib/api";
import type { ContentWorkItem } from "@wilq/shared-schemas";
import { App, createWilqQueryClient, createWilqRouter } from "./App";
vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return {
    ...actual,
    getContentWorkItemInitialDraft: vi.fn(),
    getContentWorkItemEditorialIntegrity: vi.fn(),
    getContentWorkItemRevisionHtmlPackage: vi.fn(),
    getContentRevisionTargetMapping: vi.fn(),
    getContentRevisionTargetDraftPreview: vi.fn(),
    postContentRevisionTargetMappingConfirmation: vi.fn(),
    postContentRevisionTargetDraftAction: vi.fn(),
    getContentWorkItemDecisionContext: vi.fn(),
    getContentSelectedWorkspace: vi.fn(),
    getContentInventoryCatalog: vi.fn(),
    getContentOperatorContext: vi.fn(),
    getContentWorkItemQueue: vi.fn(),
    getContentWorkItemSnapshot: vi.fn(),
    postContentWorkItemInitialDraft: vi.fn(),
    postContentWorkItemWordPressDraftExecution: vi.fn(),
    saveContentWorkItemDraftRevision: vi.fn(),
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
    vi.mocked(getContentWorkItemDecisionContext).mockResolvedValue(contentDecisionContext());
    vi.mocked(getContentSelectedWorkspace).mockResolvedValue(selectedWorkspace());
    vi.mocked(getContentInventoryCatalog).mockResolvedValue(contentInventoryCatalog());
    vi.mocked(getContentWorkItemQueue).mockResolvedValue(contentQueueResponse());
    vi.mocked(getContentWorkItemSnapshot).mockResolvedValue(workflowSnapshot());
    vi.mocked(postContentWorkItemInitialDraft).mockResolvedValue(initialDraftResponse());
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
    expect(screen.getByText(/dokładny stan dokumentu i materiały zapisane przy tej rewizji/)).toBeInTheDocument();
    expect(screen.queryByText(/przygotowany dokument i uczciwe różnice/)).not.toBeInTheDocument();
    expect(screen.getByText(/Nie ma jeszcze zapisanej rewizji/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Nowa wersja" }));
    expect(screen.getAllByText("Nowa wersja nie została jeszcze przygotowana")).toHaveLength(3);
  });

  it.each(["review=1", "text=1&review=1"])(
    "opens the exact review route when navigation queue reads reject (%s)",
    async (reviewSearch) => {
      vi.mocked(getContentWorkItemQueue).mockRejectedValue(new Error("Kolejka niedostępna"));
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
      expect(getContentWorkItemQueue).not.toHaveBeenCalled();
      expect(getContentWorkItemDecisionContext).not.toHaveBeenCalled();
      expect(getContentWorkItemInitialDraft).not.toHaveBeenCalled();
      expect(getContentWorkItemSnapshot).not.toHaveBeenCalled();
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
    fireEvent.click(screen.getByRole("button", { name: /przejdź do review/i }));
    await waitFor(() => expect(appRouter.state.location.pathname).toBe("/content-workflow/content_work_item_bdo"));
    expect(appRouter.state.location.search.view).toBe("review");
  });

  it("keeps an exact missing review route separate from a warm catalogue entry", async () => {
    vi.mocked(getContentSelectedWorkspace).mockRejectedValue(new Error("Nie znaleziono strony"));
    const client = createWilqQueryClient({ defaultOptions: { queries: { retry: false } } });
    client.setQueryData(["content-workflow", "queue", "catalog"], contentQueueResponse());

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
    expect(getContentWorkItemQueue).not.toHaveBeenCalled();
    expect(screen.queryByTestId("content-review-workspace")).not.toBeInTheDocument();
  });

  it("shows exact observed target options and requires an explicit mapping confirmation", async () => {
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
    fireEvent.click(screen.getByText("Przypisanie dokumentu do dev", { exact: true }));

    expect(await screen.findByText("Zaobserwowane możliwości układu")).toBeInTheDocument();
    expect(screen.getByText("https://ekologus.dev.proudsite.pl/bdo/")).toBeInTheDocument();
    expect(screen.getByText("Pole układu: content_sections")).toBeInTheDocument();
    expect(screen.getByText("Dostępne układy: text_section")).toBeInTheDocument();
    expect(screen.getByText(/nie decyzja, gdzie trafi element dokumentu/)).toBeInTheDocument();
    expect(screen.getByTestId("target-mapping-confirmation")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Zapisz potwierdzenie przypisania" })).toBeDisabled();
    expect(postContentRevisionTargetMappingConfirmation).not.toHaveBeenCalled();
    expect(getContentRevisionTargetMapping).toHaveBeenCalledWith(
      "content_work_item_bdo",
      workspace.canonical_document.revision_id
    );
    expect(postContentWorkItemWordPressDraftExecution).not.toHaveBeenCalled();
  });

  it("stores a human mapping confirmation without creating a WordPress draft", async () => {
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

    fireEvent.click(await screen.findByText("Przypisanie dokumentu do dev", { exact: true }));
    await screen.findByTestId("target-mapping-confirmation");
    fireEvent.change(screen.getByLabelText("Potwierdza"), { target: { value: "Marta Kowalska" } });
    fireEvent.change(screen.getByLabelText("Layout"), { target: { value: "text_section" } });
    fireEvent.change(screen.getByLabelText("Nagłówek sekcji"), { target: { value: "heading" } });
    fireEvent.change(screen.getByLabelText("Treść sekcji"), { target: { value: "content_html" } });
    fireEvent.click(screen.getByRole("button", { name: "Zapisz potwierdzenie przypisania" }));

    await waitFor(() => expect(postContentRevisionTargetMappingConfirmation).toHaveBeenCalledWith(
      workspace.work_item_id,
      preview.revision.revision_id,
      expect.objectContaining({
        confirmed_by: "Marta Kowalska",
        expected_revision_digest: preview.revision.content_digest,
        expected_target_contract_digest: "b".repeat(64),
        expected_binding_digest: "c".repeat(64)
      })
    ));
    expect(postContentWorkItemWordPressDraftExecution).not.toHaveBeenCalled();
  });

  it("offers the approved document package from Text without opening a WordPress path", async () => {
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

    expect(await screen.findByTestId("content-approved-html-package")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Pobierz paczkę dokumentu" })).toBeInTheDocument();
    expect(getContentWorkItemRevisionHtmlPackage).not.toHaveBeenCalled();
    expect(postContentWorkItemWordPressDraftExecution).not.toHaveBeenCalled();
  });

  it("creates a separate exact dev-draft action without writing to WordPress", async () => {
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

    fireEvent.click(await screen.findByText("Podgląd danych do szkicu na dev", { exact: true }));
    await screen.findByText("Dane są gotowe do osobnego sprawdzenia");
    fireEvent.click(screen.getByRole("button", { name: "Przygotuj akcję szkicu na dev" }));

    await waitFor(() =>
      expect(postContentRevisionTargetDraftAction).toHaveBeenCalledWith(
        workspace.work_item_id,
        preview.revision.revision_id,
        expect.objectContaining({
          expected_revision_digest: preview.revision.content_digest,
          expected_target_contract_digest: preview.target?.target_contract_digest,
          expected_confirmation_digest: preview.confirmation?.confirmation_digest,
          expected_payload_digest: preview.payload_digest
        })
      )
    );
    expect(screen.getByRole("link", { name: "Otwórz akcję szkicu" })).toHaveAttribute(
      "href",
      "/actions/act_content_dev_draft_1"
    );
    expect(postContentWorkItemWordPressDraftExecution).not.toHaveBeenCalled();
  });

  it("names a page target as a page when its authoring surface is unknown", async () => {
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
    fireEvent.click(screen.getByText("Przypisanie dokumentu do dev", { exact: true }));

    expect(await screen.findByText("Znaleziono stronę na dev")).toBeInTheDocument();
    expect(screen.queryByText("Znaleziono artykuł na dev")).not.toBeInTheDocument();
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
    expect(postContentWorkItemWordPressDraftExecution).not.toHaveBeenCalled();
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

});



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
        title: "BDO i sprawozdawczość środowiskowa",
        summary: "Zatwierdzona karta wiedzy dotycząca usługi BDO."
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
  review?: ContentWorkItemWorkflowSnapshotResponse["human_review"]["review"];
  handoff?: ContentWorkItemWorkflowSnapshotResponse["wordpress_handoff"]["handoff_result"]["handoff"];
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
    goal: "refresh_existing" as const,
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
    document_kind: "refresh_existing",
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
