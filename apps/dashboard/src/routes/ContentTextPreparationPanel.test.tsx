import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  getContentRegulatorySourceFactProposal,
  getContentWorkItemInitialDraft,
  getContentWorkItemPlanningProposal,
  postContentRegulatorySourceFactProposal,
  postContentRegulatorySourceFactProposalReview,
  postContentWorkItemInitialDraft,
  postContentWorkItemPlanningProposal
} from "../lib/api";
import { ContentTextPreparationPanel } from "./ContentTextPreparationPanel";

vi.mock("../lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../lib/api")>()),
  getContentWorkItemInitialDraft: vi.fn(),
  getContentWorkItemPlanningProposal: vi.fn(),
  getContentRegulatorySourceFactProposal: vi.fn(),
  postContentRegulatorySourceFactProposal: vi.fn(),
  postContentRegulatorySourceFactProposalReview: vi.fn(),
  postContentWorkItemInitialDraft: vi.fn(),
  postContentWorkItemPlanningProposal: vi.fn()
}));

function renderPanel(onSelectedWorkspaceRead?: () => Promise<unknown>) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return {
    client,
    ...render(<QueryClientProvider client={client}>
      {onSelectedWorkspaceRead ? <SelectedWorkspaceObserver read={onSelectedWorkspaceRead} /> : null}
      <ContentTextPreparationPanel workItemId="work_item" />
    </QueryClientProvider>)
  };
}

function SelectedWorkspaceObserver({ read }: { read: () => Promise<unknown> }) {
  useQuery({
    queryKey: ["content-workflow", "work-item", "work_item", "selected-workspace"],
    queryFn: read,
    staleTime: Infinity
  });
  return null;
}

function readyToGenerate(status: "not_generated" | "failed" = "not_generated") {
  return {
    status,
    work_item_id: "work_item",
    service_card_id: "service_card",
    planning_input_digest: "a".repeat(64),
    proposal: null,
    blockers: [],
    input_summary: {
      final_canonical_url: "https://ekologus.pl/bdo/",
      service_label: "BDO",
      inventory_status: "available",
      content_inventory_status: "available",
      source_assessments: [],
      source_fact_count: 0,
      source_fact_ids: [],
      source_material_ids: [],
      evidence_id_count: 0,
      knowledge_card_count: 0,
      measurement_metrics: []
    },
    safe_next_step: "Przygotuj strukturę.",
    publish_ready: false
  };
}

function readyRegulatoryProposal(proposalId = "regulatory_fact_proposal_scope", snapshotId = "regulatory_snapshot_scope") {
  return {
    status: "ready",
    proposal: {
      proposal_id: proposalId,
      candidate_id: "bdo_registration_scope_2026_07_31_r2",
      profile_id: "bdo",
      profile_version: "2026-07",
      source_url: "https://bdo.mos.gov.pl/baza-wiedzy/kto-podlega-pod-obowiazek-rejestracji/",
      source_snapshot_id: snapshotId,
      source_snapshot_digest: "d".repeat(64),
      observed_on: "2026-07-31",
      proposed_fact: `Zakres obowiązku z propozycji ${proposalId} wymaga dalszej oceny dla konkretnej działalności.`,
      covered_requirement_ids: ["bdo_scope"],
      codex_run_id: `codex_${proposalId}`,
      status: "ready",
      human_review_required: true,
      created_at: "2026-07-31T12:00:00Z"
    },
    reason: "Pobrano snapshot.",
    safe_next_step: "Sprawdź źródło."
  };
}

describe("ContentTextPreparationPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getContentRegulatorySourceFactProposal).mockResolvedValue({
      status: "not_generated",
      reason: "Brak propozycji.",
      safe_next_step: "Przygotuj propozycję."
    });
  });
  afterEach(cleanup);

  it("starts one exact planning request from the ready state with one marketer-facing action", async () => {
    vi.mocked(getContentWorkItemPlanningProposal).mockResolvedValue(readyToGenerate() as never);
    vi.mocked(postContentWorkItemPlanningProposal).mockResolvedValueOnce({ ...readyToGenerate(), status: "generating", safe_next_step: "Poczekaj na strukturę." } as never);
    renderPanel();

    fireEvent.click(await screen.findByRole("button", { name: "Przygotuj tekst" }));
    await waitFor(() => expect(postContentWorkItemPlanningProposal).toHaveBeenCalledWith({
      service_card_id: "service_card",
      expected_planning_input_digest: "a".repeat(64),
      operator_hint: "",
      requested_by: "wilku"
    }, "work_item"));
    expect(screen.queryByText("Następny krok")).not.toBeInTheDocument();
    expect(screen.queryByText(/zatwierdź plan/i)).not.toBeInTheDocument();
  });

  it("continues one requested text flow from a generated structure to the exact first draft", async () => {
    vi.mocked(getContentWorkItemPlanningProposal)
      .mockResolvedValueOnce(readyToGenerate() as never)
      .mockResolvedValue(readyPlan() as never);
    vi.mocked(postContentWorkItemPlanningProposal).mockResolvedValueOnce({
      ...readyToGenerate(),
      status: "generating"
    } as never);
    vi.mocked(postContentWorkItemInitialDraft).mockResolvedValueOnce({
      status: "generating",
      work_item_id: "work_item",
      proposal_id: "proposal_1",
      run_id: "run_1",
      blockers: [],
      safe_next_step: "Poczekaj.",
      publish_ready: false,
      runtime: { status: "started", thread_id: null, turn_id: null, external_call_attempted: false }
    } as never);
    vi.mocked(getContentWorkItemInitialDraft).mockResolvedValue({
      status: "generating",
      work_item_id: "work_item",
      proposal_id: "proposal_1",
      run_id: "run_1",
      blockers: [],
      safe_next_step: "Poczekaj.",
      publish_ready: false,
      runtime: { status: "started", thread_id: null, turn_id: null, external_call_attempted: false }
    } as never);
    renderPanel();

    fireEvent.click(await screen.findByRole("button", { name: "Przygotuj tekst" }));

    await waitFor(() => expect(postContentWorkItemInitialDraft).toHaveBeenCalledWith({
      expected_proposal_id: "proposal_1",
      expected_planning_digest: "c".repeat(64),
      expected_planning_input_digest: "a".repeat(64),
      requested_by: "wilku"
    }, "work_item"));
  });

  it("uses an exact ready proposal to start the first text without a plan-approval step", async () => {
    vi.mocked(getContentWorkItemPlanningProposal).mockResolvedValueOnce(readyPlan() as never);
    vi.mocked(postContentWorkItemInitialDraft).mockResolvedValueOnce({
      status: "generating",
      work_item_id: "work_item",
      proposal_id: "proposal_1",
      run_id: "run_1",
      blockers: [],
      safe_next_step: "Poczekaj.",
      publish_ready: false,
      runtime: { status: "started", thread_id: null, turn_id: null, external_call_attempted: false }
    } as never);
    vi.mocked(getContentWorkItemInitialDraft).mockResolvedValue({
      status: "generating",
      work_item_id: "work_item",
      proposal_id: "proposal_1",
      run_id: "run_1",
      blockers: [],
      safe_next_step: "Poczekaj.",
      publish_ready: false,
      runtime: { status: "started", thread_id: null, turn_id: null, external_call_attempted: false }
    } as never);
    renderPanel();

    fireEvent.click(await screen.findByRole("button", { name: "Przygotuj tekst" }));
    await waitFor(() => expect(postContentWorkItemInitialDraft).toHaveBeenCalledWith({
      expected_proposal_id: "proposal_1",
      expected_planning_digest: "c".repeat(64),
      expected_planning_input_digest: "a".repeat(64),
      requested_by: "wilku"
    }, "work_item"));
    expect(screen.queryByText("Szkic struktury tekstu")).not.toBeInTheDocument();
  });

  it("does not leak an internal plan-approval instruction into the marketer recovery action", async () => {
    vi.mocked(getContentWorkItemPlanningProposal).mockResolvedValue({
      ...readyToGenerate(),
      status: "blocked",
      blockers: [{
        code: "service_card_not_approved",
        label: "Brakuje zatwierdzonego źródła",
        reason: "Nie można jeszcze oprzeć tekstu na wybranej wiedzy.",
        next_step: "Zatwierdź plan."
      }]
    } as never);
    renderPanel();

    const recovery = (await screen.findByText(/Co wymaga uwagi:/)).parentElement;
    expect(recovery).toHaveTextContent("Brakuje zatwierdzonego źródła");
    expect(recovery).toHaveTextContent("Wybierz zatwierdzone źródło wiedzy, na którym ma oprzeć się tekst.");
    expect(screen.queryByText("Zatwierdź plan.")).not.toBeInTheDocument();
  });

  it("shows an official regulatory candidate as review-only, never as planning evidence", async () => {
    vi.mocked(getContentWorkItemPlanningProposal).mockResolvedValue({
      ...readyToGenerate(),
      status: "blocked",
      blockers: [{
        code: "missing_regulatory_source_coverage",
        label: "Brakuje zatwierdzonego źródła urzędowego",
        reason: "Zakres BDO wymaga review źródła urzędowego.",
        next_step: "Sprawdź źródło."
      }],
      input_summary: {
        ...readyToGenerate().input_summary,
        regulatory_profile_id: "bdo",
        regulatory_profile_version: "2026-07",
        regulatory_requirement_ids: ["bdo_scope"],
        regulatory_source_fact_ids: [],
        regulatory_requirement_coverage: [{
          requirement_id: "bdo_scope",
          label: "Zakres obowiązku",
          reason: "Wymaga źródła urzędowego.",
          source_fact_ids: [],
          evidence_ids: []
        }],
        regulatory_review_candidates: [{
          candidate_id: "bdo_scope_candidate",
          source_url: "https://bdo.mos.gov.pl/baza-wiedzy/kto-podlega-pod-obowiazek-rejestracji/",
          source_title: "BDO: Kto podlega pod obowiązek rejestracji?",
          observed_on: "2026-07-31",
          requirement_ids: ["bdo_scope"],
          requirement_labels: ["Zakres obowiązku"],
          review_status: "review_required",
          safe_next_step: "Sprawdź zakres z ekspertem przed zatwierdzeniem faktu."
        }]
      }
    } as never);
    renderPanel();

    fireEvent.click(await screen.findByText("Na jakich danych oprze się tekst"));

    const evidence = screen.getByTestId("content-planning-evidence");
    expect(evidence).toHaveTextContent("Źródła urzędowe do sprawdzenia przed przygotowaniem treści");
    expect(evidence).toHaveTextContent("nie są jeszcze dowodem w planie");
    expect(evidence).toHaveTextContent("BDO: Kto podlega pod obowiązek rejestracji?");
    expect(evidence).toHaveTextContent("Zakres obowiązku");
    expect(screen.queryByRole("button", { name: "Przygotuj tekst" })).not.toBeInTheDocument();
  });

  it("records a human regulatory fact only after an exact official-source snapshot", async () => {
    vi.mocked(getContentWorkItemPlanningProposal).mockResolvedValue({
      ...readyToGenerate(),
      status: "blocked",
      blockers: [{
        code: "missing_regulatory_source_coverage",
        label: "Brakuje zatwierdzonego źródła urzędowego",
        reason: "Zakres BDO wymaga review źródła urzędowego.",
        next_step: "Sprawdź źródło."
      }],
      input_summary: {
        ...readyToGenerate().input_summary,
        regulatory_profile_id: "bdo",
        regulatory_profile_version: "2026-07",
        regulatory_requirement_ids: ["bdo_scope"],
        regulatory_source_fact_ids: [],
        regulatory_requirement_coverage: [{
          requirement_id: "bdo_scope",
          source_fact_ids: [],
          evidence_ids: []
        }],
        regulatory_review_candidates: [{
          candidate_id: "bdo_registration_scope_2026_07_31_r2",
          source_url: "https://bdo.mos.gov.pl/baza-wiedzy/kto-podlega-pod-obowiazek-rejestracji/",
          source_title: "BDO: Kto podlega pod obowiązek rejestracji?",
          observed_on: "2026-07-31",
          requirement_ids: ["bdo_scope"],
          requirement_labels: ["Zakres obowiązku"],
          review_status: "review_required",
          safe_next_step: "Sprawdź źródło."
        }]
      }
    } as never);
    vi.mocked(postContentRegulatorySourceFactProposal).mockResolvedValue(
      readyRegulatoryProposal("proposal_post_p1", "snapshot_p1") as never
    );
    vi.mocked(getContentRegulatorySourceFactProposal)
      .mockResolvedValueOnce({ status: "not_generated", reason: "Brak propozycji.", safe_next_step: "Przygotuj propozycję." } as never)
      .mockResolvedValue(readyRegulatoryProposal("proposal_get_p2", "snapshot_p2") as never);
    vi.mocked(postContentRegulatorySourceFactProposalReview).mockResolvedValue({
      review_id: "regulatory_review_scope",
      candidate_id: "bdo_registration_scope_2026_07_31_r2",
      profile_id: "bdo",
      profile_version: "2026-07",
      service_card_ids: ["ekologus_service_bdo_reporting"],
      source_url: "https://bdo.mos.gov.pl/baza-wiedzy/kto-podlega-pod-obowiazek-rejestracji/",
      source_title: "BDO: Kto podlega pod obowiązek rejestracji?",
      observed_on: "2026-07-31",
      source_snapshot_id: "regulatory_snapshot_scope",
      source_snapshot_digest: "d".repeat(64),
      reviewed_fact: "Zakres obowiązku wymaga dalszej oceny dla konkretnej działalności.",
      covered_requirement_ids: ["bdo_scope"],
      decision: "accepted",
      reviewer: "Wilku",
      reviewed_at: "2026-07-31T12:01:00Z"
    } as never);
    renderPanel();

    fireEvent.click(await screen.findByText("Na jakich danych oprze się tekst"));
    fireEvent.click(screen.getByRole("button", { name: "Przygotuj propozycję do review" }));
    await screen.findByText("Zakres obowiązku z propozycji proposal_get_p2 wymaga dalszej oceny dla konkretnej działalności.");
    fireEvent.click(await screen.findByRole("button", { name: "Przyjmij propozycję po review" }));

    await waitFor(() => expect(postContentRegulatorySourceFactProposalReview).toHaveBeenCalledWith("proposal_get_p2", {
      expected_source_snapshot_id: "snapshot_p2",
      expected_source_snapshot_digest: "d".repeat(64),
      decision: "accepted",
      reviewer: "Wilku"
    }));
    expect(screen.queryByRole("button", { name: "Przygotuj tekst" })).not.toBeInTheDocument();
  });

  it("records the exact persisted regulatory proposal after a reload without a proposal POST", async () => {
    vi.mocked(getContentWorkItemPlanningProposal).mockResolvedValue({
      ...readyToGenerate(),
      status: "blocked",
      blockers: [{
        code: "missing_regulatory_source_coverage",
        label: "Brakuje zatwierdzonego źródła urzędowego",
        reason: "Zakres BDO wymaga review źródła urzędowego.",
        next_step: "Sprawdź źródło."
      }],
      input_summary: {
        ...readyToGenerate().input_summary,
        regulatory_review_candidates: [{
          candidate_id: "bdo_registration_scope_2026_07_31_r2",
          source_url: "https://bdo.mos.gov.pl/baza-wiedzy/kto-podlega-pod-obowiazek-rejestracji/",
          source_title: "BDO: Kto podlega pod obowiązek rejestracji?",
          observed_on: "2026-07-31",
          requirement_ids: ["bdo_scope"],
          requirement_labels: ["Zakres obowiązku"],
          review_status: "review_required",
          safe_next_step: "Sprawdź źródło."
        }]
      }
    } as never);
    vi.mocked(getContentRegulatorySourceFactProposal).mockResolvedValue(
      readyRegulatoryProposal("proposal_reload", "snapshot_reload") as never
    );
    vi.mocked(postContentRegulatorySourceFactProposalReview).mockResolvedValue({
      review_id: "regulatory_review_reload",
      candidate_id: "bdo_registration_scope_2026_07_31_r2",
      profile_id: "bdo",
      profile_version: "2026-07",
      service_card_ids: ["ekologus_service_bdo_reporting"],
      source_url: "https://bdo.mos.gov.pl/baza-wiedzy/kto-podlega-pod-obowiazek-rejestracji/",
      source_title: "BDO: Kto podlega pod obowiązek rejestracji?",
      observed_on: "2026-07-31",
      source_snapshot_id: "snapshot_reload",
      source_snapshot_digest: "d".repeat(64),
      reviewed_fact: "Zakres obowiązku z propozycji proposal_reload wymaga dalszej oceny dla konkretnej działalności.",
      covered_requirement_ids: ["bdo_scope"],
      decision: "accepted",
      reviewer: "Wilku",
      reviewed_at: "2026-07-31T12:01:00Z"
    } as never);
    renderPanel();

    fireEvent.click(await screen.findByText("Na jakich danych oprze się tekst"));
    fireEvent.click(await screen.findByRole("button", { name: "Przyjmij propozycję po review" }));

    await waitFor(() => expect(postContentRegulatorySourceFactProposalReview).toHaveBeenCalledWith("proposal_reload", {
      expected_source_snapshot_id: "snapshot_reload",
      expected_source_snapshot_digest: "d".repeat(64),
      decision: "accepted",
      reviewer: "Wilku"
    }));
    expect(postContentRegulatorySourceFactProposal).not.toHaveBeenCalled();
  });

  it("shows only exact planning evidence and GSC queries used by the ready plan", async () => {
    vi.mocked(getContentWorkItemPlanningProposal).mockResolvedValue({
      ...readyPlan(),
      input_summary: {
        ...readyToGenerate().input_summary,
        source_material_ids: ["material_1", "material_2"],
        knowledge_card_count: 3,
        evidence_id_count: 4,
        source_assessments: [
          { source: "wordpress", status: "used", reason: "Dokładny materiał.", evidence_ids: [] },
          { source: "gsc", status: "used", reason: "Dokładne zapytania.", evidence_ids: [] },
          { source: "ahrefs", status: "missing", reason: "Brak powiązania.", evidence_ids: [] }
        ]
      },
      proposal: {
        ...readyPlan().proposal,
        search_demand: {
          gsc_query_rows: [
            { term: "bdo dla firm", period: "2026-07", impressions: 181, clicks: 4 },
            { term: "bdo dla firm", period: "2026-06", impressions: 150, clicks: 3 },
            ...Array.from({ length: 5 }, (_, index) => ({ term: `zapytanie ${index}`, period: "2026-07", impressions: index, clicks: null }))
          ]
        }
      }
    } as never);
    renderPanel();

    fireEvent.click(await screen.findByText("Na jakich danych oprze się tekst"));

    expect(screen.getByTestId("content-planning-evidence")).toHaveTextContent("Materiały źródłowe");
    expect(screen.getByTestId("content-planning-evidence")).toHaveTextContent("Google Search Console");
    expect(screen.getByTestId("content-planning-evidence")).toHaveTextContent("Wykorzystane. Dokładny materiał.");
    expect(screen.getByTestId("content-planning-evidence")).toHaveTextContent("Wykorzystane. Dokładne zapytania.");
    expect(screen.getByTestId("content-planning-evidence")).toHaveTextContent("bdo dla firm · okres: 2026-07 · 181 wyświetleń · 4 kliknięć");
    expect(screen.getByTestId("content-planning-evidence")).toHaveTextContent("bdo dla firm · okres: 2026-06 · 150 wyświetleń · 3 kliknięć");
    expect(screen.getByTestId("content-planning-evidence")).toHaveTextContent("Pokazano 6 z 7 exact zapytań GSC.");
    expect(screen.getByTestId("content-planning-evidence")).toHaveTextContent("Ahrefs");
  });

  it("shows evidence-bound GSC queries from the current input before a plan exists", async () => {
    vi.mocked(getContentWorkItemPlanningProposal).mockResolvedValue({
      ...readyToGenerate(),
      status: "blocked",
      blockers: [{
        code: "missing_regulatory_source_coverage",
        label: "Brakuje zatwierdzonych źródeł urzędowych",
        reason: "Źródła urzędowe wymagają decyzji człowieka.",
        next_step: "Sprawdź źródła."
      }],
      input_summary: {
        ...readyToGenerate().input_summary,
        gsc_query_rows: [{
          source_kind: "gsc_query",
          source_connector: "google_search_console",
          term: "bdo co to",
          page: "https://ekologus.pl/bdo/",
          landing_match_tiers: ["exact"],
          service_card_id: "service_card",
          alignment_basis: "gsc_exact_page",
          review_required: true,
          section_headings: [],
          section_mapping_status: "page_only",
          period: "2026-07",
          freshness: "fresh",
          collected_at: null,
          evidence_ids: ["ev_gsc_bdo"],
          impressions: 181,
          clicks: 4,
          ctr: null,
          average_position: null,
          average_monthly_searches: null,
          cost_micros: null,
          conversions: null,
          conversion_value: null
        }]
      }
    } as never);
    renderPanel();

    fireEvent.click(await screen.findByText("Na jakich danych oprze się tekst"));

    const evidence = screen.getByTestId("content-planning-evidence");
    expect(evidence).toHaveTextContent("bdo co to · okres: 2026-07 · 181 wyświetleń · 4 kliknięć");
  });

  it("distinguishes an exact measurement comparison from an unavailable trend", async () => {
    vi.mocked(getContentWorkItemPlanningProposal).mockResolvedValue({
      ...readyToGenerate(),
      input_summary: {
        ...readyToGenerate().input_summary,
        metric_comparisons: [{
          source_connector: "google_search_console",
          status: "available",
          baseline_period: "2026-06",
          comparison_period: "2026-07",
          metric_names: ["clicks", "impressions"],
          baseline_values: { clicks: 12, impressions: 140 },
          comparison_values: { clicks: 18, impressions: 210 },
          evidence_ids: ["ev_gsc_periods"],
          reason: "Dwa dokładne okresy tej strony."
        }, {
          source_connector: "google_analytics_4",
          status: "not_available",
          baseline_period: null,
          comparison_period: null,
          metric_names: [],
          baseline_values: {},
          comparison_values: {},
          evidence_ids: [],
          reason: "Brakuje dwóch odrębnych, dokładnych okresów tego samego adresu."
        }]
      }
    } as never);
    renderPanel();

    fireEvent.click(await screen.findByText("Na jakich danych oprze się tekst"));

    const comparisons = screen.getByTestId("content-planning-measurement-comparisons");
    expect(comparisons).toHaveTextContent("Google Search Console");
    expect(comparisons).toHaveTextContent("Dokładne okresy: 2026-06 → 2026-07");
    expect(comparisons).toHaveTextContent("Kliknięcia: 12 → 18");
    expect(comparisons).toHaveTextContent("Wyświetlenia: 140 → 210");
    expect(comparisons).toHaveTextContent("Google Analytics 4: brak bezpiecznego porównania");
    expect(comparisons).toHaveTextContent("Brakuje dwóch odrębnych, dokładnych okresów tego samego adresu.");
    expect(comparisons).not.toHaveTextContent("zmiana:");
  });

  it("replaces a POST planning state with fresher exact query evidence", async () => {
    const inputA = { ...readyToGenerate().input_summary, source_material_ids: ["material_a"], evidence_id_count: 1 };
    const inputB = { ...readyToGenerate().input_summary, source_material_ids: ["material_b", "material_c"], evidence_id_count: 2 };
    vi.mocked(getContentWorkItemPlanningProposal)
      .mockResolvedValueOnce({ ...readyToGenerate(), input_summary: inputA } as never)
      .mockResolvedValue({ ...readyToGenerate(), status: "blocked", input_summary: inputB, blockers: [{ code: "stale_input", label: "Nowe dane", reason: "B", next_step: "Odśwież." }] } as never);
    vi.mocked(postContentWorkItemPlanningProposal).mockResolvedValueOnce({ ...readyToGenerate(), status: "generating", input_summary: inputA } as never);
    const { client } = renderPanel();
    fireEvent.click(await screen.findByRole("button", { name: "Przygotuj tekst" }));
    await client.refetchQueries({ queryKey: ["content-workflow", "work-item", "work_item", "planning-proposal"] });
    fireEvent.click(await screen.findByText("Na jakich danych oprze się tekst"));
    await waitFor(() => expect(screen.getByTestId("content-planning-evidence")).toHaveTextContent("2"));
    expect(screen.getByTestId("content-planning-evidence")).not.toHaveTextContent("material_a");
    expect(screen.queryByText("Przygotowuję pierwszy tekst")).not.toBeInTheDocument();
  });

  it("does not let a delayed planning POST overwrite a newer exact query", async () => {
    const terminalB = { ...readyToGenerate(), status: "blocked", blockers: [{ code: "stale_input", label: "Nowe dane", reason: "Stan B.", next_step: "Odśwież." }] };
    let resolveInvalidationGet!: (value: unknown) => void;
    vi.mocked(getContentWorkItemPlanningProposal)
      .mockResolvedValueOnce(readyToGenerate() as never)
      .mockResolvedValueOnce(terminalB as never)
      .mockImplementationOnce(() => new Promise((resolve) => { resolveInvalidationGet = resolve; }) as never);
    let resolvePost!: (value: unknown) => void;
    vi.mocked(postContentWorkItemPlanningProposal).mockImplementationOnce(() => new Promise((resolve) => { resolvePost = resolve; }) as never);
    const { client } = renderPanel();
    fireEvent.click(await screen.findByRole("button", { name: "Przygotuj tekst" }));
    await waitFor(() => expect(postContentWorkItemPlanningProposal).toHaveBeenCalledTimes(1));
    const queryKey = ["content-workflow", "work-item", "work_item", "planning-proposal"];
    await client.refetchQueries({ queryKey });
    await waitFor(() => expect(screen.getByText("Stan B.")).toBeInTheDocument());
    expect(screen.queryByText("Przygotowuję pierwszy tekst")).not.toBeInTheDocument();
    expect(screen.queryByText(/Przygotowuję materiał roboczy/)).not.toBeInTheDocument();
    resolvePost({ ...readyToGenerate(), status: "generating" });
    await waitFor(() => expect(getContentWorkItemPlanningProposal).toHaveBeenCalledTimes(3));
    await waitFor(() => expect(client.getQueryData(queryKey)).toMatchObject({ status: "blocked" }));
    expect(screen.getByText("Stan B.")).toBeInTheDocument();
    expect(screen.queryByText("Przygotowuję pierwszy tekst")).not.toBeInTheDocument();
    expect(screen.queryByText(/Przygotowuję materiał roboczy/)).not.toBeInTheDocument();
    resolveInvalidationGet(terminalB);
  });

  it("lets the marketer retry the same exact proposal after draft preparation fails", async () => {
    vi.mocked(getContentWorkItemPlanningProposal).mockResolvedValue(readyPlan() as never);
    vi.mocked(postContentWorkItemInitialDraft)
      .mockRejectedValueOnce(new Error("draft failed"))
      .mockResolvedValueOnce({
        status: "generating",
        work_item_id: "work_item",
        proposal_id: "proposal_1",
        run_id: "run_1",
        blockers: [],
        safe_next_step: "Poczekaj.",
        publish_ready: false,
        runtime: { status: "started", thread_id: null, turn_id: null, external_call_attempted: false }
      } as never);
    vi.mocked(getContentWorkItemInitialDraft).mockResolvedValue({
      status: "generating",
      work_item_id: "work_item",
      proposal_id: "proposal_1",
      run_id: "run_1",
      blockers: [],
      safe_next_step: "Poczekaj.",
      publish_ready: false,
      runtime: { status: "started", thread_id: null, turn_id: null, external_call_attempted: false }
    } as never);
    renderPanel();

    fireEvent.click(await screen.findByRole("button", { name: "Przygotuj tekst" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Nie udało się przygotować tekstu.");
    fireEvent.click(screen.getByRole("button", { name: "Przygotuj tekst" }));

    await waitFor(() => expect(postContentWorkItemInitialDraft).toHaveBeenCalledTimes(2));
  });

  it("refreshes the exact workspace when asynchronous draft preparation finishes", async () => {
    vi.mocked(getContentWorkItemPlanningProposal).mockResolvedValue(readyPlan() as never);
    vi.mocked(postContentWorkItemInitialDraft).mockResolvedValueOnce(initialDraft("generating") as never);
    vi.mocked(getContentWorkItemInitialDraft).mockResolvedValueOnce(initialDraft("created") as never);
    const selectedWorkspaceRead = vi.fn().mockResolvedValue({ canonical_document: { status: "created" } });
    const { client } = renderPanel(selectedWorkspaceRead);
    const invalidateQueries = vi.spyOn(client, "invalidateQueries");

    fireEvent.click(await screen.findByRole("button", { name: "Przygotuj tekst" }));

    await waitFor(() => expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: ["content-workflow", "work-item", "work_item", "selected-workspace"]
    }));
    await waitFor(() => expect(selectedWorkspaceRead).toHaveBeenCalledTimes(3));
  });

  it("polls a retried exact draft through its terminal workspace refresh", async () => {
    vi.mocked(getContentWorkItemPlanningProposal).mockResolvedValue(readyPlan() as never);
    vi.mocked(postContentWorkItemInitialDraft)
      .mockResolvedValueOnce(initialDraft("generating") as never)
      .mockResolvedValueOnce(initialDraft("generating") as never);
    vi.mocked(getContentWorkItemInitialDraft)
      .mockResolvedValueOnce(initialDraft("failed") as never)
      .mockResolvedValueOnce(initialDraft("generating") as never)
      .mockResolvedValueOnce(initialDraft("created") as never);
    const selectedWorkspaceRead = vi.fn().mockResolvedValue({ canonical_document: { status: "created" } });
    const { client } = renderPanel(selectedWorkspaceRead);

    fireEvent.click(await screen.findByRole("button", { name: "Przygotuj tekst" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Przygotuj tekst" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Przygotuj tekst" }));

    await waitFor(() => expect(postContentWorkItemInitialDraft).toHaveBeenCalledTimes(2));
    await client.refetchQueries({ queryKey: ["content-workflow", "work-item", "work_item", "initial-draft"] });
    await client.refetchQueries({ queryKey: ["content-workflow", "work-item", "work_item", "initial-draft"] });
    await waitFor(() => expect(getContentWorkItemInitialDraft).toHaveBeenCalledTimes(3));
    await waitFor(() => expect(selectedWorkspaceRead).toHaveBeenCalledTimes(4));
  });

  it("releases the exact draft guard when POST returns a typed terminal failure", async () => {
    vi.mocked(getContentWorkItemPlanningProposal).mockResolvedValue(readyPlan() as never);
    vi.mocked(postContentWorkItemInitialDraft)
      .mockResolvedValueOnce(initialDraft("failed") as never)
      .mockResolvedValueOnce(initialDraft("generating") as never);
    renderPanel();

    fireEvent.click(await screen.findByRole("button", { name: "Przygotuj tekst" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Przygotuj tekst" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Przygotuj tekst" }));

    await waitFor(() => expect(postContentWorkItemInitialDraft).toHaveBeenCalledTimes(2));
  });
});

function readyPlan() {
  return {
    ...readyToGenerate(),
    status: "ready",
    proposal: {
      proposal_id: "proposal_1",
      planning_digest: "c".repeat(64)
    }
  };
}

function initialDraft(status: "generating" | "created" | "failed") {
  return {
    status,
    work_item_id: "work_item",
    proposal_id: "proposal_1",
    run_id: "run_1",
    blockers: status === "failed" ? [{
      code: "runtime_failed",
      label: "Nie udało się przygotować tekstu",
      reason: "Worker zakończył się błędem.",
      next_step: "Spróbuj ponownie."
    }] : [],
    safe_next_step: status === "created" ? "Otwórz tekst." : "Poczekaj.",
    publish_ready: false,
    runtime: { status: status === "failed" ? "failed" : "started", thread_id: null, turn_id: null, external_call_attempted: false }
  };
}
