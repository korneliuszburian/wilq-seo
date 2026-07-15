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
  type ContentWorkItemWordPressDraftHandoffResponse,
  type ContentWorkItemWorkflowSnapshotResponse,
  type ContentWorkItemSnapshotResponse
} from "../lib/api";

export type ContentWorkflowSnapshot = {
  freshnessAssessment: ContentFreshnessAssessment;
  candidate: ContentWorkItemQueueCandidate;
  serviceProfileContext: ContentWorkItemWorkflowSnapshotResponse["service_profile_context"];
  claimLedger: ContentClaimLedger;
  preflight: ContentWorkItemPreflightResponse;
  salesBrief: ContentWorkItemSalesBriefResponse;
  draftPackage: ContentWorkItemDraftPackageResponse;
  structuredGenerationReadiness: ContentWorkItemWorkflowSnapshotResponse["structured_generation_readiness"];
  humanReview: ContentWorkItemHumanReviewResponse;
  wordpressHandoff: ContentWorkItemWordPressDraftHandoffResponse;
  measurementWindow: ContentWorkItemMeasurementWindowResponse;
  revisionWorkspace: ContentWorkItemWorkflowSnapshotResponse["revision_workspace"];
  planningWorkspace: ContentWorkItemWorkflowSnapshotResponse["planning_workspace"];
  currentStepId: WorkflowStepId;
  operatorSteps: WorkflowStep[];
};

type ApiWorkflowStep = ContentWorkItemWorkflowSnapshotResponse["operator_steps"][number];

export type WorkflowStepId = ApiWorkflowStep["id"];
export type WorkflowStep = {
  id: WorkflowStepId;
  title: string;
  phase: ApiWorkflowStep["phase"];
  readiness: ApiWorkflowStep["readiness"];
  statusLabel: string;
  summary: string;
  canOpen: boolean;
  canSubmit: boolean;
  blocker: ApiWorkflowStep["blocker"];
  safeNextStep: string;
};

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
    serviceProfileContext: snapshot.service_profile_context,
    claimLedger: snapshot.claim_ledger,
    preflight: snapshot.preflight,
    salesBrief: snapshot.sales_brief,
    draftPackage: snapshot.draft_package,
    structuredGenerationReadiness: snapshot.structured_generation_readiness,
    humanReview: snapshot.human_review,
    wordpressHandoff: snapshot.wordpress_handoff,
    measurementWindow: snapshot.measurement_window,
    revisionWorkspace: snapshot.revision_workspace,
    planningWorkspace: snapshot.planning_workspace,
    currentStepId: snapshot.current_step_id,
    operatorSteps: snapshot.operator_steps.map((step) => ({
      id: step.id,
      title: step.title,
      phase: step.phase,
      readiness: step.readiness,
      statusLabel: step.status_label,
      summary: step.summary,
      canOpen: step.can_open,
      canSubmit: step.can_submit,
      blocker: step.blocker,
      safeNextStep: step.safe_next_step
    }))
  };
}
