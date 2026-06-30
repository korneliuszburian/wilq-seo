import {
  postContentWorkItemDraftPackage,
  postContentWorkItemHumanReview,
  postContentWorkItemMeasurementWindow,
  postContentWorkItemPreflight,
  postContentWorkItemSalesBrief,
  postContentWorkItemWordPressDraftHandoff,
  type ContentWorkItemDraftPackageResponse,
  type ContentWorkItemHumanReviewResponse,
  type ContentWorkItemPreflightResponse,
  type ContentWorkItemSalesBriefResponse,
  type ContentWorkItemWordPressDraftHandoffResponse
} from "../lib/api";

export type ContentWorkflowSnapshot = {
  preflight: ContentWorkItemPreflightResponse;
  salesBrief: ContentWorkItemSalesBriefResponse;
  draftPackage: ContentWorkItemDraftPackageResponse;
  humanReview: ContentWorkItemHumanReviewResponse;
  wordpressHandoff: ContentWorkItemWordPressDraftHandoffResponse;
  measurementWindow: Awaited<ReturnType<typeof postContentWorkItemMeasurementWindow>>;
};

export type WorkflowStep = { title: string; status: string; summary: string };

export async function loadContentWorkflowSnapshot(): Promise<ContentWorkflowSnapshot> {
  const runtime = workflowRuntime();
  const preflight = await loadPreflight(runtime);
  const salesBrief = await loadSalesBrief(runtime);
  const brief = salesBrief.sales_brief_result.brief;
  const draftPackage = await loadDraftPackage(runtime, brief);
  const draft = draftPackage.draft_package_result.draft_package;
  const humanReview = await loadHumanReview(runtime, brief?.id, draft);
  const wordpressHandoff = await loadWordPressHandoff(humanReview, draft);
  const measurementWindow = await loadMeasurementWindow(runtime, brief?.id, draft, wordpressHandoff);
  return { preflight, salesBrief, draftPackage, humanReview, wordpressHandoff, measurementWindow };
}

export function buildWorkflowSteps(data: ContentWorkflowSnapshot): WorkflowStep[] {
  return [
    preflightStep(data.preflight),
    salesBriefStep(data.salesBrief),
    draftPackageStep(data.draftPackage),
    humanReviewStep(data.humanReview),
    wordpressHandoffStep(data.wordpressHandoff),
    measurementWindowStep(data.measurementWindow)
  ];
}

function preflightStep(preflight: ContentWorkflowSnapshot["preflight"]): WorkflowStep {
  return {
    title: "Sprawdzenie pisania",
    status: preflight.preflight_verdict.status,
    summary: preflight.preflight_verdict.next_step
  };
}

function salesBriefStep(salesBrief: ContentWorkflowSnapshot["salesBrief"]): WorkflowStep {
  const brief = salesBrief.sales_brief_result.brief;
  return {
    title: "Plan sprzedażowy",
    status: brief ? "gotowy do review" : "zablokowany",
    summary: brief?.buyer_problem ?? "Brakuje Sales Brief."
  };
}

function draftPackageStep(draftPackage: ContentWorkflowSnapshot["draftPackage"]): WorkflowStep {
  const draft = draftPackage.draft_package_result.draft_package;
  return {
    title: "Paczka szkicu",
    status: draft ? "outline do review" : "zablokowany",
    summary: "WILQ przygotowuje materiał do sprawdzenia człowieka, nie gotową publikację."
  };
}

function humanReviewStep(humanReview: ContentWorkflowSnapshot["humanReview"]): WorkflowStep {
  return {
    title: "Review człowieka",
    status: humanReview.wordpress_handoff_allowed ? "zatwierdzone" : "wymaga decyzji",
    summary: "Bez zatwierdzenia człowieka WordPress draft handoff pozostaje zablokowany."
  };
}

function wordpressHandoffStep(
  wordpressHandoff: ContentWorkflowSnapshot["wordpressHandoff"]
): WorkflowStep {
  return {
    title: "Szkic w WordPress",
    status: wordpressHandoff.handoff_result.handoff?.post_status ?? "zablokowany",
    summary: "WordPress dostaje tylko szkic po audycie. Publikacja nie jest automatyczna."
  };
}

function measurementWindowStep(
  measurementWindow: ContentWorkflowSnapshot["measurementWindow"]
): WorkflowStep {
  return {
    title: "Okno pomiaru",
    status: measurementWindow.measurement_window_result.window?.status ?? "brak",
    summary: "WILQ planuje pomiar teraz, ale ocena efektu czeka na koniec obserwacji."
  };
}

function workflowRuntime() {
  return {
    item: contentWorkItem(),
    inventoryRecords: [contentInventoryRecord()],
    claimLedger: contentClaimLedger(),
    seed: salesBriefSeed()
  };
}

function loadPreflight(runtime: ReturnType<typeof workflowRuntime>) {
  return postContentWorkItemPreflight({
    item: runtime.item,
    inventory_records: runtime.inventoryRecords,
    duplicate_risk: "clear"
  });
}

function loadSalesBrief(runtime: ReturnType<typeof workflowRuntime>) {
  return postContentWorkItemSalesBrief({
    item: {
      ...runtime.item,
      preserve_first_plan_status: "approved",
      measurement_window_status: "planned",
      measurement_window_id: "measurement_window_content_work_item_bdo"
    },
    inventory_records: runtime.inventoryRecords,
    duplicate_risk: "clear",
    claim_ledger: runtime.claimLedger,
    seed: runtime.seed
  });
}

function loadDraftPackage(
  runtime: ReturnType<typeof workflowRuntime>,
  brief: ContentWorkItemSalesBriefResponse["sales_brief_result"]["brief"]
) {
  return postContentWorkItemDraftPackage({
    item: {
      ...runtime.item,
      preflight_status: "draft_allowed",
      preserve_first_plan_status: "approved",
      sales_brief_status: "approved",
      sales_brief_id: brief?.id,
      claim_ledger_status: "approved",
      claim_ledger_id: "claim_ledger_bdo",
      measurement_window_status: "planned",
      measurement_window_id: "measurement_window_content_work_item_bdo"
    },
    inventory_records: runtime.inventoryRecords,
    duplicate_risk: "clear",
    claim_ledger: runtime.claimLedger,
    seed: runtime.seed,
    sales_brief: brief
  });
}

function loadHumanReview(
  runtime: ReturnType<typeof workflowRuntime>,
  briefId: string | null | undefined,
  draft: ContentWorkItemDraftPackageResponse["draft_package_result"]["draft_package"]
) {
  return postContentWorkItemHumanReview({
    item: {
      ...runtime.item,
      preflight_status: "handoff_allowed",
      preserve_first_plan_status: "approved",
      sales_brief_status: "approved",
      sales_brief_id: briefId,
      claim_ledger_status: "approved",
      claim_ledger_id: "claim_ledger_bdo",
      draft_package_status: "ready",
      draft_package_id: draft?.id,
      audit_status: "recorded",
      audit_id: "audit_bdo",
      measurement_window_status: "planned",
      measurement_window_id: "measurement_window_content_work_item_bdo"
    },
    review: humanReviewPayload(draft?.id),
    draft_package: draft,
    claim_ledger: runtime.claimLedger
  });
}

function loadWordPressHandoff(
  humanReview: ContentWorkItemHumanReviewResponse,
  draft: ContentWorkItemDraftPackageResponse["draft_package_result"]["draft_package"]
) {
  return postContentWorkItemWordPressDraftHandoff({
    item: humanReview.reviewed_item,
    draft_package: draft,
    human_review: humanReviewPayload(draft?.id),
    audit: handoffAudit()
  });
}

function loadMeasurementWindow(
  runtime: ReturnType<typeof workflowRuntime>,
  briefId: string | null | undefined,
  draft: ContentWorkItemDraftPackageResponse["draft_package_result"]["draft_package"],
  wordpressHandoff: ContentWorkItemWordPressDraftHandoffResponse
) {
  return postContentWorkItemMeasurementWindow({
    item: {
      ...runtime.item,
      preflight_status: "handoff_allowed",
      preserve_first_plan_status: "approved",
      sales_brief_status: "approved",
      sales_brief_id: briefId,
      claim_ledger_status: "approved",
      claim_ledger_id: "claim_ledger_bdo",
      draft_package_status: "ready",
      draft_package_id: draft?.id,
      human_review_status: "approved",
      human_review_id: "human_review_bdo",
      audit_status: "recorded",
      audit_id: "audit_bdo"
    },
    handoff: wordpressHandoff.handoff_result.handoff,
    baseline_period: { start: "2026-05-01", end: "2026-05-31" },
    observation_period: { start: "2026-07-01", end: "2026-07-31" },
    allowed_metrics: ["gsc_clicks", "gsc_impressions", "ga4_engaged_sessions"],
    source_connectors: ["google_search_console", "google_analytics_4"]
  });
}

function contentWorkItem() {
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
    duplicate_status: "checked"
  };
}

function contentInventoryRecord() {
  return {
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
  };
}

function contentClaimLedger() {
  return {
    id: "claim_ledger_bdo",
    work_item_id: "content_work_item_bdo",
    reviewed_by: "wilku",
    entries: [
      {
        id: "claim_general_bdo",
        claim_text: "Ekologus pomaga firmom uporządkować obowiązki BDO.",
        claim_type: "service_claim",
        status: "allowed_with_evidence",
        evidence_ids: ["ev_wp_bdo"],
        reason: "Claim ma przypisany dowód źródłowy.",
        reviewer_id: "wilku"
      }
    ]
  };
}

function salesBriefSeed() {
  return {
    target_reader: "właściciel firmy, który musi uporządkować obowiązki BDO",
    buyer_problem: "nie wie, czy i jak musi prowadzić ewidencję BDO",
    buyer_trigger: "zbliża się kontrola albo termin aktualizacji danych",
    search_intent: "informacyjno-usługowy",
    service_fit: "konsultacja i obsługa środowiskowa Ekologus",
    h1_direction: "BDO dla firm: co trzeba sprawdzić przed działaniem",
    h2_direction: ["Kogo dotyczy BDO", "Co warto przygotować przed konsultacją"],
    faq_direction: ["Czy każda firma musi mieć BDO?"],
    cta_direction: "Zaproponuj kontakt w celu sprawdzenia sytuacji firmy.",
    internal_link_direction: ["https://ekologus.pl/kontakt/"],
    source_facts: [
      {
        evidence_id: "ev_gsc_bdo",
        source_connector: "google_search_console",
        summary: "GSC pokazuje popyt na temat BDO."
      },
      {
        evidence_id: "ev_wp_bdo",
        source_connector: "wordpress_ekologus",
        summary: "WordPress inventory potwierdza istniejącą treść BDO."
      }
    ],
    missing_evidence: []
  };
}

function humanReviewPayload(draftPackageId?: string) {
  return {
    id: "human_review_bdo",
    work_item_id: "content_work_item_bdo",
    stage: "draft_package",
    reviewed_by: "wilku",
    decision: "approved",
    notes: "Szkic może iść dalej jako WordPress draft.",
    checked_items: ["brief zgodny z dowodami", "claimy bez gwarancji efektu"],
    evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
    blocked_claims_handled: [],
    draft_package_id: draftPackageId
  };
}

function handoffAudit() {
  return {
    audit_id: "audit_bdo",
    actor: "wilku",
    reason: "Zatwierdzony szkic może trafić do WordPress jako draft.",
    evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
    human_review_id: "human_review_bdo"
  };
}
