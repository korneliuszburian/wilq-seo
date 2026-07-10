import {
  getContentWorkItemSnapshot,
  type ContentFreshnessAssessment,
  type ContentWorkItemQueueCandidate,
  type ContentClaimLedger,
  type ContentWorkItemDraftPackageResponse,
  type ContentWorkItemHumanReviewResponse,
  type ContentWorkItemMeasurementWindowResponse,
  type ContentWorkItemPreflightResponse,
  type ContentWorkItemSalesBriefResponse,
  type ContentWorkItemStructuredDraftGenerationResponse,
  type ContentWorkItemWordPressDraftHandoffResponse,
  type ContentWorkItemSnapshotResponse
} from "../lib/api";

export type ContentWorkflowSnapshot = {
  freshnessAssessment: ContentFreshnessAssessment;
  candidate: ContentWorkItemQueueCandidate;
  claimLedger: ContentClaimLedger;
  preflight: ContentWorkItemPreflightResponse;
  salesBrief: ContentWorkItemSalesBriefResponse;
  draftPackage: ContentWorkItemDraftPackageResponse;
  structuredGeneration: ContentWorkItemStructuredDraftGenerationResponse;
  humanReview: ContentWorkItemHumanReviewResponse;
  wordpressHandoff: ContentWorkItemWordPressDraftHandoffResponse;
  measurementWindow: ContentWorkItemMeasurementWindowResponse;
  operatorSteps: WorkflowStep[];
};

export type WorkflowStep = { id: string; title: string; statusLabel: string; summary: string };

export async function loadContentWorkflowSnapshot(
  workItemId?: string
): Promise<ContentWorkflowSnapshot> {
  return workflowSnapshotFromApi(await getContentWorkItemSnapshot(workItemId));
}

function workflowSnapshotFromApi(
  snapshot: ContentWorkItemSnapshotResponse
): ContentWorkflowSnapshot {
  if (snapshot.response_type === "blocked_snapshot") {
    throw new Error(snapshot.safe_next_step);
  }
  return {
    freshnessAssessment: snapshot.freshness_assessment,
    candidate: snapshot.candidate,
    claimLedger: snapshot.claim_ledger,
    preflight: snapshot.preflight,
    salesBrief: snapshot.sales_brief,
    draftPackage: snapshot.draft_package,
    structuredGeneration: snapshot.structured_generation,
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
