import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  getContentWorkItemSnapshot,
  saveContentWorkItemSnapshotAudit,
  saveContentWorkItemSnapshotHumanReview,
  type ContentWorkItemWorkflowSnapshotResponse
} from "../lib/api";
import type { ContentWorkItem } from "@wilq/shared-schemas";
import { App, createWilqQueryClient, createWilqRouter } from "./App";

vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return {
    ...actual,
    getContentWorkItemSnapshot: vi.fn(),
    saveContentWorkItemSnapshotHumanReview: vi.fn(),
    saveContentWorkItemSnapshotAudit: vi.fn()
  };
});

describe("ContentWorkflowSurface", () => {
  beforeEach(() => {
    vi.mocked(getContentWorkItemSnapshot).mockResolvedValue(workflowSnapshot());
    vi.mocked(saveContentWorkItemSnapshotHumanReview).mockResolvedValue(
      workflowSnapshot({ review: humanReview() }).human_review
    );
    vi.mocked(saveContentWorkItemSnapshotAudit).mockResolvedValue(
      workflowSnapshot({ review: humanReview(), handoff: wordpressHandoff() }).wordpress_handoff
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

    await waitFor(() => {
      expect(screen.getByText("Workflow treści bez slopu")).toBeInTheDocument();
    });

    const workflow = screen.getByLabelText("Kroki workflow treści");
    const steps = within(workflow).getAllByRole("listitem");
    expect(steps.map((step) => within(step).getByRole("heading").textContent)).toEqual([
      "Sprawdzenie pisania",
      "Plan sprzedażowy",
      "Paczka szkicu",
      "Sprawdzenie człowieka",
      "Szkic w WordPress",
      "Okno pomiaru"
    ]);
    expect(screen.getAllByText("BDO dla firm")[0]).toBeInTheDocument();
    expect(screen.getByText("WordPress zostaje w trybie szkicu")).toBeInTheDocument();
    expect(screen.getByText(/WordPress nie dostaje jeszcze szkicu/)).toBeInTheDocument();
    expect(screen.getByText("wymaga decyzji")).toBeInTheDocument();
    expect(screen.getByText("zablokowany")).toBeInTheDocument();
    expect(screen.getByText("Nie wolno jeszcze oceniać efektu")).toBeInTheDocument();
    expect(screen.getByText(/Pierwsza ocena po 2026-08-01/)).toBeInTheDocument();
    expect(screen.getByText("Dowody: 2")).toBeInTheDocument();
    expect(screen.queryByText("/api/content")).not.toBeInTheDocument();
    expect(screen.queryByText("ContentWorkItem")).not.toBeInTheDocument();
    expect(screen.queryByText("wordpress_ekologus")).not.toBeInTheDocument();
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
  });

  it("keeps the handoff controls disabled when a draft-only handoff is already prepared", async () => {
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
    forbidden_claims: [],
    missing_evidence: [],
    evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
    source_connectors: ["google_search_console", "wordpress_ekologus"],
    measurement_plan: {
      measurement_window_id: "measurement_window_content_work_item_bdo",
      metrics_to_watch: ["GSC clicks"],
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
    draft_kind: "outline",
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
    }
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
