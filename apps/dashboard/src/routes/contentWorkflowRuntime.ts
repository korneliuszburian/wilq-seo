import {
  getContentWorkItemSnapshot,
  type ContentWorkItemDraftPackageResponse,
  type ContentWorkItemHumanReviewResponse,
  type ContentWorkItemMeasurementWindowResponse,
  type ContentWorkItemPreflightResponse,
  type ContentWorkItemSalesBriefResponse,
  type ContentWorkItemWordPressDraftHandoffResponse,
  type ContentWorkItemWorkflowSnapshotResponse
} from "../lib/api";

export type ContentWorkflowSnapshot = {
  preflight: ContentWorkItemPreflightResponse;
  salesBrief: ContentWorkItemSalesBriefResponse;
  draftPackage: ContentWorkItemDraftPackageResponse;
  humanReview: ContentWorkItemHumanReviewResponse;
  wordpressHandoff: ContentWorkItemWordPressDraftHandoffResponse;
  measurementWindow: ContentWorkItemMeasurementWindowResponse;
};

export type WorkflowStep = { title: string; status: string; summary: string };

export async function loadContentWorkflowSnapshot(): Promise<ContentWorkflowSnapshot> {
  return workflowSnapshotFromApi(await getContentWorkItemSnapshot());
}

function workflowSnapshotFromApi(
  snapshot: ContentWorkItemWorkflowSnapshotResponse
): ContentWorkflowSnapshot {
  return {
    preflight: snapshot.preflight,
    salesBrief: snapshot.sales_brief,
    draftPackage: snapshot.draft_package,
    humanReview: snapshot.human_review,
    wordpressHandoff: snapshot.wordpress_handoff,
    measurementWindow: snapshot.measurement_window
  };
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
    status: brief ? "gotowy do sprawdzenia" : "zablokowany",
    summary: brief?.buyer_problem ?? "Brakuje planu sprzedażowego."
  };
}

function draftPackageStep(draftPackage: ContentWorkflowSnapshot["draftPackage"]): WorkflowStep {
  const draft = draftPackage.draft_package_result.draft_package;
  return {
    title: "Paczka szkicu",
    status: draft ? "konspekt do sprawdzenia" : "zablokowany",
    summary: "WILQ przygotowuje materiał do sprawdzenia człowieka, nie gotową publikację."
  };
}

function humanReviewStep(humanReview: ContentWorkflowSnapshot["humanReview"]): WorkflowStep {
  return {
    title: "Sprawdzenie człowieka",
    status: humanReview.wordpress_handoff_allowed ? "zatwierdzone" : "wymaga decyzji",
    summary: "Bez zatwierdzenia człowieka przekazanie szkicu do WordPress pozostaje zablokowane."
  };
}

function wordpressHandoffStep(
  wordpressHandoff: ContentWorkflowSnapshot["wordpressHandoff"]
): WorkflowStep {
  const handoff = wordpressHandoff.handoff_result.handoff;
  const blocker = wordpressHandoff.handoff_result.blockers[0];
  return {
    title: "Szkic w WordPress",
    status: handoff?.post_status ?? "zablokowany",
    summary: handoff
      ? "WordPress dostaje tylko szkic po audycie. Publikacja nie jest automatyczna."
      : blocker?.reason ?? "WordPress nie dostaje szkicu bez sprawdzenia człowieka i audytu."
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
