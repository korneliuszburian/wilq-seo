import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  getContentWorkItemEnrichment,
  getContentWorkItemQueue,
  getContentWorkItemSnapshot,
  postContentWorkItemQualityReview,
  postContentWorkItemRevisionPlan,
  postContentWorkItemStructuredDraftPreview,
  postContentWorkItemStructuredDraftRuntime,
  postContentWorkItemWordPressDraftExecution,
  saveContentWorkItemSnapshotAudit,
  saveContentWorkItemSnapshotHumanReview,
  type ContentWorkItemQualityReviewResponse,
  type ContentOpportunityEnrichmentResponse,
  type ContentWorkItemQueueResponse,
  type ContentWorkItemRevisionPlanResponse,
  type ContentWorkItemStructuredDraftPreviewResponse,
  type ContentWorkItemStructuredDraftRuntimeResponse,
  type ContentWorkItemWordPressDraftExecutionResponse,
  type ContentWorkItemWorkflowSnapshotResponse
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
    postContentWorkItemQualityReview: vi.fn(),
    postContentWorkItemRevisionPlan: vi.fn(),
    postContentWorkItemStructuredDraftPreview: vi.fn(),
    postContentWorkItemStructuredDraftRuntime: vi.fn(),
    postContentWorkItemWordPressDraftExecution: vi.fn(),
    saveContentWorkItemSnapshotHumanReview: vi.fn(),
    saveContentWorkItemSnapshotAudit: vi.fn()
  };
});

describe("ContentWorkflowSurface", () => {
  beforeEach(() => {
    vi.mocked(getContentWorkItemEnrichment).mockResolvedValue(contentOpportunityEnrichmentResponse());
    vi.mocked(getContentWorkItemQueue).mockResolvedValue(contentQueueResponse());
    vi.mocked(getContentWorkItemSnapshot).mockResolvedValue(workflowSnapshot());
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
    vi.mocked(postContentWorkItemWordPressDraftExecution).mockResolvedValue(
      wordpressDraftExecutionResponse()
    );
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("renders the ordered content production workflow without raw technical terms", async () => {
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
      await screen.findByText("Workflow treści bez slopu", undefined, { timeout: 5000 })
    ).toBeInTheDocument();

    expect(await screen.findByText("Kolejka tematów")).toBeInTheDocument();
    expect(screen.getByText(/WILQ widzi 3 kandydatów/)).toBeInTheDocument();
    expect(screen.getByText("Zielony Ład dla firm")).toBeInTheDocument();
    expect(screen.getByText("Luka Ahrefs bez finalnego adresu")).toBeInTheDocument();
    expect(screen.getByText("odśwież istniejącą treść · gotowe do planu")).toBeInTheDocument();
    expect(screen.getAllByText(/pomiar do zaplanowania/)[0]).toBeInTheDocument();
    const workflow = screen.getByLabelText("Kroki workflow treści");
    const steps = within(workflow).getAllByRole("listitem");
    expect(steps.map((step) => within(step).getByRole("heading").textContent)).toEqual([
      "Sprawdzenie pisania",
      "Plan sprzedażowy",
      "Paczka szkicu",
      "Szkic treści",
      "Sprawdzenie człowieka",
      "Szkic w WordPress",
      "Okno pomiaru"
    ]);
    expect(screen.getAllByText("BDO dla firm")[0]).toBeInTheDocument();
    expect(screen.getByText("Wzbogacenie tematu")).toBeInTheDocument();
    expect(screen.getByText(/Firma chce wiedzieć, czy musi aktualizować obowiązki BDO/))
      .toBeInTheDocument();
    expect(screen.getByText("informacyjno-usługowa")).toBeInTheDocument();
    expect(screen.getByText("obsługa środowiskowa Ekologus")).toBeInTheDocument();
    expect(screen.getByText("GSC pokazuje popyt na temat BDO.")).toBeInTheDocument();
    expect(screen.getByText("Jakość briefu")).toBeInTheDocument();
    expect(screen.getByText("sygnał użyteczny, ale wymaga review")).toBeInTheDocument();
    expect(screen.getByText(/Brief ma ślad dowodowy, ale wiedza nadal wymaga decyzji/))
      .toBeInTheDocument();
    expect(screen.getByText("Ograniczenia wiedzy i dowody")).toBeInTheDocument();
    expect(screen.getByText(/ev_content_service_profile_source_facts/)).toBeInTheDocument();
    expect(screen.getAllByText("Szkic treści")[0]).toBeInTheDocument();
    expect(screen.getByText("WordPress zostaje w trybie szkicu")).toBeInTheDocument();
    expect(screen.getByText("Podgląd szkicu WordPress")).toBeInTheDocument();
    expect(screen.getByText("Podgląd treści")).toBeInTheDocument();
    expect(screen.getByText("Ocena jakości szkicu")).toBeInTheDocument();
    expect(screen.getByText("Plan poprawki")).toBeInTheDocument();
    expect(screen.getByText(/Ten krok nie wywołuje modelu/)).toBeInTheDocument();
    expect(screen.getByText(/Po wygenerowaniu szkicu WILQ pokaże treść/)).toBeInTheDocument();
    expect(screen.getByText(/WordPress nie dostaje jeszcze szkicu/)).toBeInTheDocument();
    expect(screen.getByText(/Ten krok nie wykonuje zewnętrznego zapisu/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sprawdź gotowość szkicu" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Pokaż podgląd treści" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Sprawdź jakość szkicu" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Pokaż plan poprawki" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Sprawdź podgląd szkicu" })).toBeDisabled();
    expect(screen.getByText("wymaga decyzji")).toBeInTheDocument();
    expect(screen.getByText("zablokowany")).toBeInTheDocument();
    expect(screen.getByText("Nie wolno jeszcze oceniać efektu")).toBeInTheDocument();
    expect(screen.getByText(/Pierwsza ocena po 2026-08-01/)).toBeInTheDocument();
    expect(screen.getByText("Dowody: 2")).toBeInTheDocument();
    expect(screen.queryByText("/api/content")).not.toBeInTheDocument();
    expect(screen.queryByText("ContentWorkItem")).not.toBeInTheDocument();
    expect(screen.queryByText("wordpress_ekologus")).not.toBeInTheDocument();
    expect(screen.queryByText("json_schema")).not.toBeInTheDocument();
    expect(screen.queryByText("responses.create")).not.toBeInTheDocument();
  });

  it("submits a snapshot human review from the current API snapshot", async () => {
    const client = createWilqQueryClient({
      defaultOptions: { queries: { retry: false } }
    });
    render(
      <App
        appRouter={createWilqRouter({ initialPath: "/content-workflow", defaultPendingMinMs: 0 })}
        client={client}
      />
    );

    await screen.findByRole("button", { name: "Zatwierdź sprawdzenie" });
    fireEvent.click(screen.getByRole("button", { name: "Zatwierdź sprawdzenie" }));

    await waitFor(() => {
      expect(saveContentWorkItemSnapshotHumanReview).toHaveBeenCalled();
    });
    expect(vi.mocked(saveContentWorkItemSnapshotHumanReview).mock.calls[0]?.[0]).toEqual({
        review: expect.objectContaining({
          id: "human_review_content_work_item_bdo",
          work_item_id: "content_work_item_bdo",
          stage: "draft_package",
          reviewed_by: "wilku",
          decision: "approved",
          draft_package_id: "draft_package_content_work_item_bdo",
          evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"]
        })
      });
    expect(saveContentWorkItemSnapshotAudit).not.toHaveBeenCalled();
    expect(postContentWorkItemStructuredDraftRuntime).not.toHaveBeenCalled();
    expect(postContentWorkItemStructuredDraftPreview).not.toHaveBeenCalled();
    expect(postContentWorkItemWordPressDraftExecution).not.toHaveBeenCalled();
  });

  it("submits a matching audit only after WILQ exposes an approved human review", async () => {
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

    await screen.findByRole("button", { name: "Zapisz audyt przekazania" });
    fireEvent.click(screen.getByRole("button", { name: "Zapisz audyt przekazania" }));

    await waitFor(() => {
      expect(saveContentWorkItemSnapshotAudit).toHaveBeenCalled();
    });
    expect(vi.mocked(saveContentWorkItemSnapshotAudit).mock.calls[0]?.[0]).toEqual({
        audit: {
          audit_id: "audit_content_work_item_bdo",
          actor: "wilku",
          reason:
            "Operator zatwierdził przekazanie wyłącznie w trybie szkicu. WordPress może dostać wyłącznie szkic.",
          evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
          human_review_id: "human_review_content_work_item_bdo"
        }
    });
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
    expect(screen.getByText("Kogo dotyczy BDO")).toBeInTheDocument();
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
      claim_ledger: null,
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

    expect(await screen.findByRole("button", { name: "Sprawdzenie zapisane" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Audyt zapisany" })).toBeDisabled();
    expect(screen.getByText(/przekazanie do WordPress pozostaje przygotowane tylko jako szkic/))
      .toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Sprawdź podgląd szkicu" }));

    await waitFor(() => {
      expect(postContentWorkItemWordPressDraftExecution).toHaveBeenCalled();
    });
    expect(vi.mocked(postContentWorkItemWordPressDraftExecution).mock.calls[0]?.[0]).toEqual({
      handoff: wordpressHandoff(),
      draft_package: draftPackage(),
      mode: "dry_run"
    });
    expect(await screen.findByRole("button", { name: "Podgląd szkicu gotowy" })).toBeDisabled();
    expect(screen.getByText(/WordPress dostałby status draft/)).toBeInTheDocument();
    expect(screen.getByText(/Publikacja: zablokowana/)).toBeInTheDocument();
    expect(screen.getByText(/Nadpisywanie treści: zablokowane/)).toBeInTheDocument();
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
    operator_summary:
      "WILQ widzi 3 kandydatów i 2 mogą przejść do planu bez omijania dowodów.",
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

function contentOpportunityEnrichmentResponse(): ContentOpportunityEnrichmentResponse {
  return {
    enrichment: {
      id: "content_opportunity_enrichment_content_work_item_bdo",
      work_item_id: "content_work_item_bdo",
      decision_id: "decision_bdo",
      title: "BDO dla firm",
      topic: "BDO dla firm",
      recommended_mode: "refresh",
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
      recommended_mode: "refresh",
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
        constraint_type: "evidence_requirement",
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
    sections: [],
    section_to_evidence_map: [],
    claims_used: [],
    claims_removed_or_blocked: [],
    human_review_questions: ["Czy to brzmi jak Ekologus?"],
    publish_ready: false
  };
}

function workflowSnapshot({
  review = null,
  handoff = null
}: {
  review?: ReturnType<typeof humanReview> | null;
  handoff?: ReturnType<typeof wordpressHandoff> | null;
} = {}): ContentWorkItemWorkflowSnapshotResponse {
  const reviewedItem = review
    ? workItem({ human_review_status: "approved", human_review_id: review.id })
    : workItem({ human_review_status: "missing", human_review_id: null });
  return {
    response_type: "workflow_snapshot",
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
    operator_steps: operatorSteps({ review: Boolean(review), handoff: Boolean(handoff) })
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
          constraint_type: "evidence_requirement",
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

function operatorSteps({ review, handoff }: { review: boolean; handoff: boolean }) {
  return [
    {
      id: "content_preflight",
      title: "Sprawdzenie pisania",
      status_label: "można planować",
      summary: "Przejdź do kolejnego kroku."
    },
    {
      id: "sales_brief",
      title: "Plan sprzedażowy",
      status_label: "gotowy do sprawdzenia",
      summary: "nie wie, jak podejść do BDO"
    },
    {
      id: "draft_package",
      title: "Paczka szkicu",
      status_label: "konspekt do sprawdzenia",
      summary: "WILQ przygotowuje materiał do sprawdzenia człowieka, nie gotową publikację."
    },
    {
      id: "structured_draft",
      title: "Szkic treści",
      status_label: "gotowy do próby",
      summary: "WILQ może sprawdzić przygotowanie szkicu bez pisania na żywo."
    },
    {
      id: "human_review",
      title: "Sprawdzenie człowieka",
      status_label: review ? "zatwierdzone" : "wymaga decyzji",
      summary: "Bez zatwierdzenia człowieka przekazanie szkicu do WordPress pozostaje zablokowane."
    },
    {
      id: "wordpress_handoff",
      title: "Szkic w WordPress",
      status_label: handoff ? "szkic" : "zablokowany",
      summary: handoff
        ? "WordPress dostaje tylko szkic po audycie. Publikacja nie jest automatyczna."
        : "WordPress handoff nie może ruszyć bez zatwierdzonego human review."
    },
    {
      id: "measurement_window",
      title: "Okno pomiaru",
      status_label: "zaplanowane",
      summary: "WILQ planuje pomiar teraz, ale ocena efektu czeka na koniec obserwacji."
    }
  ];
}
