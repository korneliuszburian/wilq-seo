import type { ContentWorkItemQueueResponse } from "../lib/api";
import { ContentWorkflowClaimSummary } from "./ContentWorkflowClaimSummary";
import { ContentWorkflowDecisionHeader } from "./ContentWorkflowDecisionHeader";
import { ContentWorkflowNextDecisionPanel } from "./ContentWorkflowNextDecisionPanel";
import { ContentWorkflowPublicationBlockers } from "./ContentWorkflowPublicationBlockers";
import { activeWorkflowStepIndex, blockedWorkflowSteps, claimLedgerSummary } from "./contentWorkflowDecisionModel";
import type { ContentWorkflowSnapshot, WorkflowStep } from "./contentWorkflowRuntime";
import { workflowStepShortLabel } from "./WorkflowStepper";

type ContentWorkflowDecisionPanelProps = {
  data: ContentWorkflowSnapshot;
  queue: ContentWorkItemQueueResponse;
  steps: WorkflowStep[];
};

export function ContentWorkflowDecisionPanel({ data, queue, steps }: ContentWorkflowDecisionPanelProps) {
  const item = data.preflight.item;
  const blockedSteps = blockedWorkflowSteps(data.operatorSteps);
  const activeCandidate = queue.candidates.find((candidate) => candidate.work_item_id === item.id);
  const activeStepIndex = activeWorkflowStepIndex(steps, data.currentStepId);
  const activeStep = steps[activeStepIndex] ?? steps[0] ?? null;
  const ledgerSummary = claimLedgerSummary(data);
  const nextStep = activeCandidate?.safe_next_step ?? data.preflight.preflight_verdict.next_step ?? activeStep?.summary ?? "Najpierw domknij decyzję operatora i bramki publikacji.";
  const decisionTitle = activeCandidate ? `${activeCandidate.recommended_mode_label}: ${activeCandidate.title}` : `${data.preflight.preflight_verdict.recommended_mode}: ${item.topic}`;
  const decisionReason = activeCandidate?.reason ?? data.preflight.preflight_verdict.next_step ?? "WILQ pokazuje ten temat jako aktywną pracę po sprawdzeniu źródeł i bramek treści.";

  return (
    <section className="mb-6 rounded-md border border-line bg-white">
      <ContentWorkflowDecisionHeader topic={item.topic} activeStepIndex={activeStepIndex} steps={steps} />
      <div className="grid gap-4 p-4 lg:grid-cols-[1.05fr_0.95fr]">
        <ContentWorkflowNextDecisionPanel activeStepLabel={activeStep ? workflowStepShortLabel(activeStep) : "Plan"} decisionTitle={decisionTitle} decisionReason={decisionReason} evidenceCount={new Set(item.evidence_ids).size} reviewClaims={ledgerSummary.review} blockedClaims={ledgerSummary.blocked} nextStep={nextStep} />
        <ContentWorkflowPublicationBlockers steps={blockedSteps} />
      </div>
      <ContentWorkflowClaimSummary allowed={ledgerSummary.allowed} review={ledgerSummary.review} blocked={ledgerSummary.blocked} />
    </section>
  );
}
