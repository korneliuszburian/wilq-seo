import { marketerWorkflowStepTitle, type WorkflowStep, type WorkflowStepId } from "./contentWorkflowRuntime";

type ContentWorkflowTaskMapProps = {
  currentStepId: WorkflowStepId;
  selectedStepId: WorkflowStepId;
  steps: WorkflowStep[];
  sectionMapCurrent: boolean;
  onSelectStep: (stepId: WorkflowStepId) => void;
};

export function ContentWorkflowTaskMap({
  currentStepId,
  selectedStepId,
  steps,
  sectionMapCurrent,
  onSelectStep
}: ContentWorkflowTaskMapProps) {
  const visibleSteps = steps.filter((step) => step.id !== "section_map");
  const canonicalStepId = (stepId: WorkflowStepId): WorkflowStepId =>
    stepId === "section_map" ? (sectionMapCurrent ? "draft" : "scope") : stepId;
  const visibleSelectedStepId = canonicalStepId(selectedStepId);
  const visibleCurrentStepId = canonicalStepId(currentStepId);
  const selectedStep = visibleSteps.find((step) => step.id === visibleSelectedStepId) ?? visibleSteps[0];
  const currentStep = visibleSteps.find((step) => step.id === visibleCurrentStepId) ?? visibleSteps[0];

  if (!selectedStep || !currentStep) return null;

  return (
    <section
      aria-labelledby="content-workflow-task-map-title"
      className="wilq-enter wilq-enter-delay-3 mb-3 rounded-md border border-line bg-white px-3 py-2 sm:mb-4 sm:px-4"
      data-testid="content-workflow-task-map"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="content-workflow-task-map-title" className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Stan pracy
        </h2>
        <p className="text-xs text-slate-600">
          <span className="font-semibold text-ink">{marketerWorkflowStepTitle(currentStep.id)}</span>
          {selectedStep.id !== currentStep.id ? ` · otwarty: ${marketerWorkflowStepTitle(selectedStep.id)}` : ""}
        </p>
      </div>

      <ol className="mt-2 grid grid-cols-4 gap-1" aria-label="Stany pracy nad treścią">
        {visibleSteps.map((step, index) => {
          const isCurrent = step.id === visibleCurrentStepId;
          const isSelected = step.id === visibleSelectedStepId;
          return (
            <li key={step.id} className="min-w-0 shrink-0 sm:min-w-max lg:min-w-0">
              <button
                type="button"
                aria-current={isCurrent ? "step" : undefined}
                aria-pressed={isSelected}
                aria-label={`${index + 1}. ${marketerWorkflowStepTitle(step.id)}: ${step.statusLabel}`}
                disabled={!step.canOpen}
                onClick={() => onSelectStep(step.id)}
                className={`flex min-w-0 w-full flex-col items-center justify-center gap-1 rounded-md border px-1 py-1.5 text-center text-xs font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-60 sm:flex-row sm:justify-start sm:gap-2 sm:px-2 sm:text-left ${
                  isSelected
                    ? "border-action bg-action/10 text-action"
                    : step.phase === "complete" && step.readiness === "ready"
                      ? "border-go/30 bg-go/5 text-go"
                      : step.readiness === "review_required"
                        ? "border-wait/40 bg-wait/10 text-wait"
                      : "border-line bg-surface text-slate-600"
                }`}
              >
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-current text-[10px] font-bold sm:h-6 sm:w-6 sm:text-[11px]">{index + 1}</span>
                <span className="min-w-0 max-w-full text-left">
                  <span className="block break-words text-[11px] leading-tight sm:text-sm">{marketerWorkflowStepTitle(step.id)}</span>
                </span>
              </button>
            </li>
          );
        })}
      </ol>

    </section>
  );
}
