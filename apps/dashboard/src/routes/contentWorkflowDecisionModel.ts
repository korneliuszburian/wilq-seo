import type {
  ContentWorkflowSnapshot,
  WorkflowStep,
  WorkflowStepId
} from "./contentWorkflowRuntime";

export function activeWorkflowStepIndex(steps: WorkflowStep[], currentStepId: WorkflowStepId) {
  return steps.findIndex((step) => step.id === currentStepId);
}

export function blockedWorkflowSteps(steps: WorkflowStep[]) {
  return steps.filter((step) => step.readiness !== "ready");
}

export function claimLedgerSummary(data: ContentWorkflowSnapshot) {
  const allowed = data.claimLedger.entries.filter((entry) =>
    entry.status.startsWith("allowed")
  ).length;
  const review = data.claimLedger.entries.filter(
    (entry) => entry.status === "needs_human_review" || entry.strength === "weak"
  ).length;
  const blocked = data.claimLedger.entries.filter(
    (entry) => entry.status === "blocked" || entry.status === "blocked_until_measurement"
  ).length;
  return { allowed, review, blocked };
}
