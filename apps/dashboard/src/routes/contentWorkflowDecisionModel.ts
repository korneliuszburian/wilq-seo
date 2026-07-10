import type { ContentWorkflowSnapshot, WorkflowStep } from "./contentWorkflowRuntime";

export function activeWorkflowStepIndex(steps: WorkflowStep[]) {
  const blockedIndex = steps.findIndex((step) =>
    step.statusLabel.toLowerCase().includes("zablok")
  );
  if (blockedIndex >= 0) return blockedIndex;

  const reviewIndex = steps.findIndex((step) =>
    step.statusLabel.toLowerCase().includes("wymaga")
  );
  return reviewIndex >= 0 ? reviewIndex : Math.min(steps.length - 1, 1);
}

export function blockedWorkflowSteps(steps: WorkflowStep[]) {
  return steps.filter((step) => {
    const status = step.statusLabel.toLowerCase();
    return status.includes("zablok") || status.includes("brakuje") || status.includes("wymaga");
  });
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
