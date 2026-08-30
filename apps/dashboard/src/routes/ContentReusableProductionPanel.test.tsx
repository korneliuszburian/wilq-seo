import { QueryClientProvider, useQuery } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  ContentInitialDraftResponseSchema,
  ContentSelectedWorkspaceSchema
} from "@wilq/shared-schemas";
import {
  getContentRevisionTargetDraftPreview,
  getContentRevisionTargetMapping,
  getContentWorkItemInitialDraft,
  getContentWorkItemPlanningProposal,
  getContentWorkItemTargetDiscovery,
  postContentRevisionTargetDraftAction,
  postContentWorkItemInitialDraft,
  postContentWorkItemPlanningProposal,
  type ContentSelectedWorkspace
} from "../lib/api";
import { createWilqQueryClient } from "./App";
import { ContentTextWorkspace } from "./ContentWorkflowSections/TextWorkspaceSection";

vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return {
    ...actual,
    getContentRevisionTargetDraftPreview: vi.fn(),
    getContentRevisionTargetMapping: vi.fn(),
    getContentWorkItemInitialDraft: vi.fn(),
    getContentWorkItemPlanningProposal: vi.fn(),
    getContentWorkItemTargetDiscovery: vi.fn(),
    postContentRevisionTargetDraftAction: vi.fn(),
    postContentWorkItemInitialDraft: vi.fn(),
    postContentWorkItemPlanningProposal: vi.fn()
  };
});

const currentWorkItemId = "content_work_item_current_bdo";
const retainedWorkItemId = "content_work_item_retained_bdo";
const revisionId = "content_revision_retained_bdo";
const classificationRunId = "content_production_classification_w4";
const classificationRunDigest = digest("a");
const decisionSetDigest = digest("b");
const revisionDigest = digest("c");

describe("ContentReusableProductionPanel", () => {
  beforeEach(() => {
    vi.mocked(postContentWorkItemInitialDraft).mockResolvedValue(reusedInitialDraftResponse());
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("revalidates a retained alias once and keeps the retained v1 document separate", async () => {
    const selected = reuseSelectedWorkspace();
    const client = createWilqQueryClient({ defaultOptions: { queries: { retry: false } } });
    const firstMount = renderWorkspace(selected, client);

    const panel = await screen.findByTestId("content-reusable-production-panel");
    await waitFor(() => expect(postContentWorkItemInitialDraft).toHaveBeenCalledWith({
      expected_production_classification_run_digest: classificationRunDigest,
      requested_by: "wilku"
    }, retainedWorkItemId));
    expect(postContentWorkItemInitialDraft).toHaveBeenCalledTimes(1);

    const retained = await screen.findByTestId("content-retained-v1-preview");
    expect(retained).toHaveTextContent("Zachowana zatwierdzona wersja BDO");
    expect(retained).toHaveTextContent("Zakres BDO dla firmy");
    expect(retained).toHaveTextContent("Dokładna zachowana treść sekcji.");
    expect(retained).toHaveTextContent("Jak zacząć sprawdzanie BDO?");
    expect(retained).toHaveTextContent("Opisz sytuację firmy przed rozmową.");
    expect(retained).toHaveTextContent("Usługi BDO");
    expect(screen.queryByRole("button", { name: /przygotuj/i })).not.toBeInTheDocument();
    expect(panel.compareDocumentPosition(screen.getByTestId("content-document-state"))).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING
    );

    fireEvent.click(screen.getByText("Dokładne identyfikatory rewizji i review"));
    expect(screen.getByText(`Właściciel rewizji: ${retainedWorkItemId}`)).toBeInTheDocument();
    expect(screen.getByText(`Review: review_${revisionId}`)).toBeInTheDocument();
    expect(screen.getByText(`Digest rewizji: ${revisionDigest}`)).toBeInTheDocument();
    expectNoPlanningOrActionCalls();

    firstMount.unmount();
    renderWorkspace(selected, client);
    await screen.findByTestId("content-retained-approved-document");
    expect(postContentWorkItemInitialDraft).toHaveBeenCalledTimes(1);
    expectNoPlanningOrActionCalls();
  });

  it.each([
    ["mismatch", mismatchedReusedInitialDraftResponse(), "Odśwież wybrany workspace"],
    ["409 conflict", conflictInitialDraftResponse(), "Sprawdź klasyfikację przed ponowną próbą."]
  ])("fails closed for a %s response", async (_label, response, safeStep) => {
    vi.mocked(postContentWorkItemInitialDraft).mockResolvedValue(response);
    const client = createWilqQueryClient({ defaultOptions: { queries: { retry: false } } });
    renderWorkspace(reuseSelectedWorkspace(), client);

    const failure = await screen.findByTestId("content-reuse-fail-closed");
    expect(failure).toHaveTextContent("Nie pokazuję zachowanej wersji");
    expect(failure).toHaveTextContent(safeStep);
    expect(screen.queryByTestId("content-retained-approved-document")).not.toBeInTheDocument();
    expect(postContentWorkItemInitialDraft).toHaveBeenCalledTimes(1);
    expectNoPlanningOrActionCalls();
  });

  it.each([
    ["blocked reusable document", reuseSelectedWorkspace("blocked"), "Zachowana rewizja wymaga ponownego sprawdzenia."],
    ["refresh decision", guardedSelectedWorkspace("refresh"), "Odśwież dokładne źródła przed dalszą pracą."],
    ["write decision", guardedSelectedWorkspace("write"), "Przygotuj nową decyzję produkcyjną przed dalszą pracą."],
    ["blocked decision", guardedSelectedWorkspace("blocked"), "Usuń blocker przed dalszą pracą."]
  ])("shows the exact safe step without requests for %s", async (_label, selected, safeStep) => {
    const client = createWilqQueryClient({ defaultOptions: { queries: { retry: false } } });
    renderWorkspace(selected, client);

    const blocker = await screen.findByTestId("content-classified-production-blocker");
    expect(blocker).toHaveTextContent(safeStep);
    expect(screen.queryByTestId("content-reusable-production-panel")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /przygotuj/i })).not.toBeInTheDocument();
    expect(postContentWorkItemInitialDraft).not.toHaveBeenCalled();
    expectNoPlanningOrActionCalls();
  });

  it("waits for the exact operator identity before reuse revalidation", async () => {
    const client = createWilqQueryClient({ defaultOptions: { queries: { retry: false } } });
    renderWorkspace(reuseSelectedWorkspace(), client, null);

    expect(await screen.findByTestId("content-reuse-requester-pending")).toBeInTheDocument();
    expect(postContentWorkItemInitialDraft).not.toHaveBeenCalled();
    expectNoPlanningOrActionCalls();
  });
});

function renderWorkspace(
  selected: ContentSelectedWorkspace,
  client: ReturnType<typeof createWilqQueryClient>,
  requestedBy: string | null = "wilku"
) {
  return render(
    <QueryClientProvider client={client}>
      <SelectedWorkspaceHarness selected={selected} requestedBy={requestedBy} />
    </QueryClientProvider>
  );
}

function SelectedWorkspaceHarness({
  selected,
  requestedBy
}: {
  selected: ContentSelectedWorkspace;
  requestedBy: string | null;
}) {
  const selectedWorkspace = useQuery({
    queryKey: ["content-reuse-w4-test", selected.requested_work_item_id],
    queryFn: async () => selected,
    initialData: selected,
    staleTime: Infinity
  });

  return <ContentTextWorkspace
    workItemId={selected.requested_work_item_id}
    selectedWorkspace={selectedWorkspace}
    requestedBy={requestedBy}
    onOpenReview={vi.fn()}
  />;
}

function expectNoPlanningOrActionCalls() {
  expect(getContentWorkItemPlanningProposal).not.toHaveBeenCalled();
  expect(postContentWorkItemPlanningProposal).not.toHaveBeenCalled();
  expect(getContentWorkItemInitialDraft).not.toHaveBeenCalled();
  expect(getContentWorkItemTargetDiscovery).not.toHaveBeenCalled();
  expect(getContentRevisionTargetMapping).not.toHaveBeenCalled();
  expect(getContentRevisionTargetDraftPreview).not.toHaveBeenCalled();
  expect(postContentRevisionTargetDraftAction).not.toHaveBeenCalled();
}

function reuseSelectedWorkspace(documentStatus: "ready" | "blocked" = "ready") {
  const reusableDocument = documentStatus === "ready" ? {
    status: "ready",
    revision: retainedRevision(),
    review: retainedReview()
  } : {
    status: "blocked",
    code: "latest_revision_drift",
    reason_pl: "Zachowana rewizja wymaga ponownego sprawdzenia.",
    safe_next_step_pl: "Sprawdź zachowaną rewizję przed dalszą pracą."
  };
  const reason = documentStatus === "blocked"
    ? "Zachowana rewizja wymaga ponownego sprawdzenia."
    : "Zachowaj dokładną zatwierdzoną rewizję.";
  const safeNextStep = documentStatus === "blocked"
    ? "Sprawdź zachowaną rewizję przed dalszą pracą."
    : "Otwórz zachowaną rewizję bez ponownego generowania.";
  const decision = {
    ...availableDecision({
      decision: "reuse",
      lookupBasis: "retained",
      retainedId: retainedWorkItemId,
      reason,
      safeNextStep
    }),
    revision_binding: revisionBinding(),
    reusable_document: reusableDocument
  };

  return ContentSelectedWorkspaceSchema.parse({
    response_type: "content_selected_workspace",
    contract_version: "content_selected_workspace_v2",
    status: "ready",
    work_item_id: currentWorkItemId,
    requested_work_item_id: retainedWorkItemId,
    production_decision: decision,
    operator_journey: operatorJourney(),
    workspace: currentWorkspace(reason),
    reason,
    safe_next_step: safeNextStep
  });
}

function guardedSelectedWorkspace(decision: "refresh" | "write" | "blocked") {
  const safeNextStep = {
    refresh: "Odśwież dokładne źródła przed dalszą pracą.",
    write: "Przygotuj nową decyzję produkcyjną przed dalszą pracą.",
    blocked: "Usuń blocker przed dalszą pracą."
  }[decision];
  const reason = {
    refresh: "Źródła klasyfikacji wymagają odświeżenia.",
    write: "Ta klasyfikacja wymaga oddzielnej decyzji produkcyjnej.",
    blocked: "Klasyfikacja zatrzymała dalszą pracę."
  }[decision];
  const blockers = decision === "write" ? [] : [productionBlocker()];

  return ContentSelectedWorkspaceSchema.parse({
    response_type: "content_selected_workspace",
    contract_version: "content_selected_workspace_v2",
    status: "ready",
    work_item_id: currentWorkItemId,
    requested_work_item_id: currentWorkItemId,
    production_decision: {
      ...availableDecision({
        decision,
        lookupBasis: "current",
        retainedId: null,
        reason,
        safeNextStep
      }),
      blockers
    },
    operator_journey: operatorJourney(),
    workspace: currentWorkspace(reason),
    reason,
    safe_next_step: safeNextStep
  });
}

function availableDecision({
  decision,
  lookupBasis,
  retainedId,
  reason,
  safeNextStep
}: {
  decision: "reuse" | "refresh" | "write" | "blocked";
  lookupBasis: "current" | "retained";
  retainedId: string | null;
  reason: string;
  safeNextStep: string;
}) {
  return {
    status: "available",
    decision,
    run_id: classificationRunId,
    run_digest: classificationRunDigest,
    decision_set_digest: decisionSetDigest,
    generation_allowed: false,
    lookup_basis: lookupBasis,
    canonical_path: "/bdo/",
    public_url: "https://ekologus.pl/bdo/",
    current_work_item_id: currentWorkItemId,
    retained_work_item_id: retainedId,
    reason_pl: reason,
    safe_next_step_pl: safeNextStep,
    blockers: [],
    primary_evidence_ids: ["ev_bdo_current"],
    lineage_evidence_ids: ["lineage_bdo_current"],
    source_connectors: ["wordpress_ekologus"],
    freshness: {
      state: "fresh",
      checked_at: "2026-08-30T10:00:00Z",
      requires_refresh: false,
      connector_ids: ["wordpress_ekologus"]
    }
  };
}

function productionBlocker() {
  return {
    code: "production_evidence_blocked",
    owner: "wilku",
    next_step_pl: "Sprawdź blocker.",
    sources: ["wordpress_ekologus"],
    blocks_initial_generation: true
  };
}

function revisionBinding() {
  return {
    current_work_item_id: currentWorkItemId,
    retained_work_item_id: retainedWorkItemId,
    revision_work_item_id: retainedWorkItemId,
    identity_reconciliation_status: "fork",
    revision_id: revisionId,
    revision_digest: revisionDigest,
    verified_draft_action_ids: ["action_retained_draft"],
    verified_draft_post_ids: ["post_retained_draft"],
    must_not_regenerate: true
  };
}

function currentWorkspace(reason: string) {
  return {
    response_type: "content_document_workspace",
    contract_version: "content_document_workspace_v2",
    work_item_id: currentWorkItemId,
    work_kind: "refresh_existing",
    service_label: "BDO",
    source_snapshot: {
      status: "available",
      status_label: "Bieżąca strona BDO",
      title: "Bieżąca strona BDO",
      url: "https://ekologus.pl/bdo/",
      extraction_method: "wordpress_rest.content",
      lead: "Kontekst obecnej strony zostaje osobno.",
      content_excerpt: null,
      ordered_sections: [],
      faq_status: "not_observed",
      cta_status: "not_observed",
      reason: "To jest bieżący workspace, nie zachowana rewizja.",
      caveats: [],
      evidence_ids: ["ev_bdo_current"]
    },
    canonical_document: {
      status: "not_created",
      revision_id: null,
      content_digest: null,
      review_state: "unreviewed",
      label: "Bieżący dokument nie jest zastępowany",
      reason: "Zachowana rewizja pozostaje osobnym materiałem do odczytu.",
      preview: null
    },
    document_lineage: {
      status: "not_recorded",
      source_material_ids: [],
      knowledge_cards: [],
      unresolved_knowledge_card_ids: [],
      reason: "Bieżący dokument nie ma rewizji do pokazania."
    },
    comparison: {
      status: "unavailable",
      reason: "Nie porównuję zachowanej rewizji z bieżącym workspace’em.",
      items: []
    },
    next_action: {
      kind: "none",
      label: "Generowanie jest wyłączone",
      reason
    },
    regulatory_review_candidates: [],
    secondary_disclosures: []
  };
}

function operatorJourney() {
  return {
    current_step_id: "draft",
    steps: [
      ["scope", "complete"],
      ["section_map", "complete"],
      ["draft", "current"],
      ["review", "pending"],
      ["dev_draft", "pending"]
    ].map(([id, phase]) => ({
      id,
      title: `Krok ${id}`,
      phase,
      readiness: "blocked",
      status_label: "Stan z API.",
      summary: "Stan z API.",
      can_open: phase !== "pending",
      can_submit: false,
      blocker: null,
      safe_next_step: "Wykonaj bezpieczny krok wskazany przez API."
    }))
  };
}

function retainedRevision() {
  return {
    schema_version: "wilq_content_draft_revision_v1",
    revision_id: revisionId,
    work_item_id: retainedWorkItemId,
    revision_number: 5,
    base_revision_id: null,
    content_digest: revisionDigest,
    draft_package_id: "draft_package_retained_bdo",
    draft_package_digest: digest("d"),
    planning_digest: null,
    planning_input_digest: null,
    service_card_id: null,
    service_digest: null,
    inventory_digest: null,
    source_material_ids: [],
    knowledge_card_ids: [],
    source_provenance: [],
    document_kind: "refresh_existing",
    final_canonical_url: "https://ekologus.pl/bdo/",
    new_page_document_identity: null,
    title: "Zachowana zatwierdzona wersja BDO",
    page_assets: null,
    sections: [{
      section_id: null,
      heading: "Zakres BDO dla firmy",
      body_markdown: "Dokładna zachowana treść sekcji.",
      content_html: null,
      query_terms: [],
      evidence_ids: ["ev_retained_bdo"],
      claim_ids: [],
      source_material_ids: [],
      knowledge_card_ids: []
    }],
    faq: [{
      faq_id: "faq_retained_bdo",
      question: "Jak zacząć sprawdzanie BDO?",
      answer_markdown: "Zacznij od aktualnej sytuacji firmy.",
      query_terms: [],
      evidence_ids: ["ev_retained_bdo"],
      claim_ids: []
    }],
    cta_blocks: [{
      cta_id: "cta_retained_bdo",
      placement: "after_content",
      body_markdown: "Opisz sytuację firmy przed rozmową.",
      evidence_ids: ["ev_retained_bdo"],
      claim_ids: []
    }],
    internal_links: [{
      link_id: "link_retained_bdo",
      placement: "after_content",
      target_url: "https://ekologus.pl/uslugi-bdo/",
      anchor_text: "Usługi BDO",
      evidence_ids: ["ev_retained_bdo"],
      claim_ids: []
    }],
    official_source_references: [],
    claim_ledger: null,
    proposal_metadata: null,
    correction_reason: null,
    publish_ready: false,
    created_by: "wilku",
    created_at: "2026-08-30T10:05:00Z"
  };
}

function retainedReview() {
  return {
    decision_id: `review_${revisionId}`,
    decision_number: 1,
    work_item_id: retainedWorkItemId,
    revision_id: revisionId,
    revision_digest: revisionDigest,
    reviewed_by: "wilku",
    principal_id: "local_operator",
    workspace_id: "ekologus_local_pilot",
    trust_level: "local_unverified",
    decision: "approved",
    notes: "",
    checked_items: ["Dokładna rewizja"],
    evidence_ids: ["ev_retained_bdo"],
    created_at: "2026-08-30T10:06:00Z"
  };
}

function reusedInitialDraftResponse() {
  return ContentInitialDraftResponseSchema.parse({
    status: "reused",
    work_item_id: currentWorkItemId,
    proposal_id: null,
    run_id: null,
    revision: retainedRevision(),
    reuse_binding: {
      classification_run_id: classificationRunId,
      classification_run_digest: classificationRunDigest,
      decision_set_digest: decisionSetDigest,
      requested_work_item_id: retainedWorkItemId,
      lookup_basis: "retained",
      current_work_item_id: currentWorkItemId,
      retained_work_item_id: retainedWorkItemId,
      revision_work_item_id: retainedWorkItemId,
      identity_reconciliation_status: "fork",
      revision_id: revisionId,
      revision_digest: revisionDigest,
      approved_review: retainedReview(),
      must_not_regenerate: true
    },
    runtime: {
      status: "not_started",
      run_id: null,
      thread_id: null,
      turn_id: null,
      event_methods: [],
      item_types: [],
      external_call_attempted: false
    },
    blockers: [],
    safe_next_step: "Otwórz dokładną zatwierdzoną rewizję.",
    publish_ready: false
  });
}

function mismatchedReusedInitialDraftResponse() {
  const response = reusedInitialDraftResponse();
  if (response.status !== "reused") throw new Error("expected reused response");
  return ContentInitialDraftResponseSchema.parse({
    ...response,
    reuse_binding: {
      ...response.reuse_binding,
      classification_run_digest: digest("e")
    }
  });
}

function conflictInitialDraftResponse() {
  return ContentInitialDraftResponseSchema.parse({
    status: "conflict",
    work_item_id: currentWorkItemId,
    proposal_id: null,
    run_id: null,
    revision: null,
    reuse_binding: null,
    runtime: {
      status: "not_started",
      run_id: null,
      thread_id: null,
      turn_id: null,
      event_methods: [],
      item_types: [],
      external_call_attempted: false
    },
    blockers: [{
      code: "revision_conflict",
      label: "Konflikt rewizji",
      reason: "Klasyfikacja wskazuje konflikt dokładnej rewizji.",
      next_step: "Sprawdź klasyfikację przed ponowną próbą.",
      source_codes: [],
      retry_after_seconds: null
    }],
    safe_next_step: "Sprawdź klasyfikację przed ponowną próbą.",
    publish_ready: false
  });
}

function digest(character: string) {
  return character.repeat(64);
}
