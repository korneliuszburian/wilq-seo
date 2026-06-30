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
  operatorSteps: WorkflowStep[];
};

export type WorkflowStep = { id: string; title: string; statusLabel: string; summary: string };

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
    measurementWindow: snapshot.measurement_window,
    operatorSteps: snapshot.operator_steps.map((step) => ({
      id: step.id,
      title: step.title,
      statusLabel: step.status_label,
      summary: step.summary
    }))
  };
}

export function buildWorkflowSteps(data: ContentWorkflowSnapshot): WorkflowStep[] {
  return data.operatorSteps;
}
