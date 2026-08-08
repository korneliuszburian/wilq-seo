import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  getContentRegulatorySourceFactProposal,
  postContentRegulatorySourceFactProposal,
  postContentRegulatorySourceFactProposalReview,
  type ContentPlanningProposalResponse
} from "../lib/api";
import { PlanningEvidenceDetails } from "./PlanningEvidenceDetails";

vi.mock("../lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../lib/api")>()),
  getContentRegulatorySourceFactProposal: vi.fn(),
  postContentRegulatorySourceFactProposal: vi.fn(),
  postContentRegulatorySourceFactProposalReview: vi.fn()
}));

type PlanningInput = NonNullable<ContentPlanningProposalResponse["input_summary"]>;
type PlanningProposal = ContentPlanningProposalResponse["proposal"];
type GscQueryRow = PlanningInput["gsc_query_rows"][number];

function planningInput(overrides: Partial<PlanningInput> = {}): PlanningInput {
  return {
    goal: "refresh_existing",
    final_canonical_url: "https://ekologus.pl/bdo/",
    service_label: "BDO",
    inventory_status: "available",
    content_inventory_status: "available",
    source_assessments: [],
    source_fact_count: 0,
    source_fact_ids: [],
    source_material_ids: [],
    gsc_query_rows: [],
    regulatory_requirement_ids: [],
    regulatory_source_fact_ids: [],
    regulatory_requirement_coverage: [],
    regulatory_review_candidates: [],
    evidence_id_count: 0,
    knowledge_card_count: 0,
    measurement_metrics: [],
    ...overrides
  };
}

function regulatoryCandidate(
  candidateId = "bdo_registration_scope_2026_07_31_r2"
): PlanningInput["regulatory_review_candidates"][number] {
  return {
    candidate_id: candidateId,
    source_url: "https://bdo.mos.gov.pl/baza-wiedzy/kto-podlega-pod-obowiazek-rejestracji/",
    source_title: "BDO: Kto podlega pod obowiązek rejestracji?",
    observed_on: "2026-07-31",
    requirement_ids: ["bdo_scope"],
    requirement_labels: ["Zakres obowiązku"],
    review_status: "review_required",
    safe_next_step: "Sprawdź zakres z ekspertem przed zatwierdzeniem faktu."
  };
}

function gscQuery(
  term: string,
  period: string,
  impressions: number | null,
  clicks: number | null
): GscQueryRow {
  return {
    source_kind: "gsc_query",
    source_connector: "google_search_console",
    term,
    page: "https://ekologus.pl/bdo/",
    landing_match_tiers: ["exact"],
    service_card_id: "service_card",
    alignment_basis: "gsc_exact_page",
    review_required: true,
    section_headings: [],
    section_mapping_status: "page_only",
    period,
    freshness: "fresh",
    collected_at: null,
    evidence_ids: [`ev_gsc_${term}_${period}`],
    impressions,
    clicks,
    ctr: null,
    average_position: null,
    average_monthly_searches: null,
    cost_micros: null,
    conversions: null,
    conversion_value: null
  };
}

function planningProposal(rows: GscQueryRow[]): NonNullable<PlanningProposal> {
  return {
    search_demand: {
      gsc_query_rows: rows
    }
  } as NonNullable<PlanningProposal>;
}

function renderEvidence(input: PlanningInput, proposal: PlanningProposal = null) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <PlanningEvidenceDetails input={input} proposal={proposal} />
    </QueryClientProvider>
  );
}

function readyRegulatoryProposal(
  proposalId = "regulatory_fact_proposal_scope",
  snapshotId = "regulatory_snapshot_scope"
) {
  return {
    status: "ready",
    proposal: {
      proposal_id: proposalId,
      candidate_id: "bdo_registration_scope_2026_07_31_r2",
      profile_id: "bdo",
      profile_version: "2026-07",
      source_url: "https://bdo.mos.gov.pl/baza-wiedzy/kto-podlega-pod-obowiazek-rejestracji/",
      source_title: "BDO: Kto podlega pod obowiązek rejestracji?",
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

describe("PlanningEvidenceDetails", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getContentRegulatorySourceFactProposal).mockResolvedValue({
      status: "not_generated",
      reason: "Brak propozycji.",
      safe_next_step: "Przygotuj propozycję."
    });
  });

  afterEach(cleanup);

  it("shows an official regulatory candidate as review-only, never as planning evidence", async () => {
    renderEvidence(planningInput({
      regulatory_review_candidates: [regulatoryCandidate("bdo_scope_candidate")]
    }));

    fireEvent.click(screen.getByText("Na jakich danych oprze się tekst"));

    const evidence = screen.getByTestId("content-planning-evidence");
    expect(evidence).toHaveTextContent("Źródła urzędowe do sprawdzenia przed przygotowaniem treści");
    expect(evidence).toHaveTextContent("nie są jeszcze dowodem w planie");
    expect(evidence).toHaveTextContent("BDO: Kto podlega pod obowiązek rejestracji?");
    expect(evidence).toHaveTextContent("Zakres obowiązku");
    expect(await screen.findByRole("button", { name: "Przygotuj propozycję do review" })).toBeEnabled();
  });

  it("records a human regulatory fact only after an exact official-source snapshot", async () => {
    vi.mocked(postContentRegulatorySourceFactProposal).mockResolvedValue(
      readyRegulatoryProposal("proposal_post_p1", "snapshot_p1") as never
    );
    vi.mocked(getContentRegulatorySourceFactProposal)
      .mockResolvedValueOnce({
        status: "not_generated",
        reason: "Brak propozycji.",
        safe_next_step: "Przygotuj propozycję."
      })
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
    renderEvidence(planningInput({
      regulatory_review_candidates: [regulatoryCandidate()]
    }));

    fireEvent.click(screen.getByText("Na jakich danych oprze się tekst"));
    fireEvent.click(screen.getByRole("button", { name: "Przygotuj propozycję do review" }));
    await screen.findByText(
      "Zakres obowiązku z propozycji proposal_get_p2 wymaga dalszej oceny dla konkretnej działalności."
    );
    fireEvent.click(screen.getByRole("button", { name: "Przyjmij propozycję po review" }));

    await waitFor(() => expect(postContentRegulatorySourceFactProposalReview).toHaveBeenCalledWith(
      "proposal_get_p2",
      {
        expected_source_snapshot_id: "snapshot_p2",
        expected_source_snapshot_digest: "d".repeat(64),
        decision: "accepted",
        reviewer: "Wilku"
      }
    ));
  });

  it("records the exact persisted regulatory proposal after a reload without a proposal POST", async () => {
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
    renderEvidence(planningInput({
      regulatory_review_candidates: [regulatoryCandidate()]
    }));

    fireEvent.click(screen.getByText("Na jakich danych oprze się tekst"));
    fireEvent.click(await screen.findByRole("button", { name: "Przyjmij propozycję po review" }));

    await waitFor(() => expect(postContentRegulatorySourceFactProposalReview).toHaveBeenCalledWith(
      "proposal_reload",
      {
        expected_source_snapshot_id: "snapshot_reload",
        expected_source_snapshot_digest: "d".repeat(64),
        decision: "accepted",
        reviewer: "Wilku"
      }
    ));
    expect(postContentRegulatorySourceFactProposal).not.toHaveBeenCalled();
  });

  it("shows only exact planning evidence and GSC queries used by the ready plan", () => {
    const rows = [
      gscQuery("bdo dla firm", "2026-07", 181, 4),
      gscQuery("bdo dla firm", "2026-06", 150, 3),
      ...Array.from(
        { length: 5 },
        (_, index) => gscQuery(`zapytanie ${index}`, "2026-07", index, null)
      )
    ];
    renderEvidence(
      planningInput({
        source_material_ids: ["material_1", "material_2"],
        knowledge_card_count: 3,
        evidence_id_count: 4,
        source_assessments: [
          {
            source: "wordpress",
            status: "used",
            reason: "Dokładny materiał.",
            landing_match_tiers: [],
            evidence_ids: [],
            knowledge_card_ids: []
          },
          {
            source: "gsc",
            status: "used",
            reason: "Dokładne zapytania.",
            landing_match_tiers: [],
            evidence_ids: [],
            knowledge_card_ids: []
          },
          {
            source: "ahrefs",
            status: "missing",
            reason: "Brak powiązania.",
            landing_match_tiers: [],
            evidence_ids: [],
            knowledge_card_ids: []
          }
        ]
      }),
      planningProposal(rows)
    );

    fireEvent.click(screen.getByText("Na jakich danych oprze się tekst"));

    const evidence = screen.getByTestId("content-planning-evidence");
    expect(evidence).toHaveTextContent("Materiały źródłowe");
    expect(evidence).toHaveTextContent("Google Search Console");
    expect(evidence).toHaveTextContent("Wykorzystane. Dokładny materiał.");
    expect(evidence).toHaveTextContent("Wykorzystane. Dokładne zapytania.");
    expect(evidence).toHaveTextContent(
      "bdo dla firm · okres: 2026-07 · 181 wyświetleń · 4 kliknięć"
    );
    expect(evidence).toHaveTextContent(
      "bdo dla firm · okres: 2026-06 · 150 wyświetleń · 3 kliknięć"
    );
    expect(evidence).toHaveTextContent("Pokazano 6 z 7 exact zapytań GSC.");
    expect(evidence).toHaveTextContent("Ahrefs");
  });

  it("shows evidence-bound GSC queries from the current input before a plan exists", () => {
    renderEvidence(planningInput({
      gsc_query_rows: [gscQuery("bdo co to", "2026-07", 181, 4)]
    }));

    fireEvent.click(screen.getByText("Na jakich danych oprze się tekst"));

    expect(screen.getByTestId("content-planning-evidence")).toHaveTextContent(
      "bdo co to · okres: 2026-07 · 181 wyświetleń · 4 kliknięć"
    );
  });

  it("distinguishes an exact measurement comparison from an unavailable trend", () => {
    renderEvidence(planningInput({
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
    }));

    fireEvent.click(screen.getByText("Na jakich danych oprze się tekst"));

    const comparisons = screen.getByTestId("content-planning-measurement-comparisons");
    expect(comparisons).toHaveTextContent("Google Search Console");
    expect(comparisons).toHaveTextContent("Dokładne okresy: 2026-06 → 2026-07");
    expect(comparisons).toHaveTextContent("Kliknięcia: 12 → 18");
    expect(comparisons).toHaveTextContent("Wyświetlenia: 140 → 210");
    expect(comparisons).toHaveTextContent(
      "Google Analytics 4: brak bezpiecznego porównania"
    );
    expect(comparisons).toHaveTextContent(
      "Brakuje dwóch odrębnych, dokładnych okresów tego samego adresu."
    );
    expect(comparisons).not.toHaveTextContent("zmiana:");
  });
});
