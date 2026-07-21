import type { WorkflowStep, WorkflowStepId } from "./contentWorkflowRuntime";

type ContentWorkflowTaskMapProps = {
  currentStepId: WorkflowStepId;
  selectedStepId: WorkflowStepId;
  steps: WorkflowStep[];
  onSelectStep: (stepId: WorkflowStepId) => void;
};

export function ContentWorkflowTaskMap({
  currentStepId,
  selectedStepId,
  steps,
  onSelectStep
}: ContentWorkflowTaskMapProps) {
  const selectedStep = steps.find((step) => step.id === selectedStepId) ?? steps[0];
  const currentStep = steps.find((step) => step.id === currentStepId) ?? steps[0];

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
          <span className="font-semibold text-ink">{currentStep.title}</span>
          {selectedStep.id !== currentStep.id ? ` · otwarty: ${selectedStep.title}` : ""}
        </p>
      </div>

      <ol className="mt-2 grid grid-cols-5 gap-1" aria-label="Etapy tworzenia treści">
        {steps.map((step, index) => {
          const isCurrent = step.id === currentStepId;
          const isSelected = step.id === selectedStepId;
          return (
            <li key={step.id} className="min-w-0 shrink-0 sm:min-w-max lg:min-w-0">
              <button
                type="button"
                aria-current={isCurrent ? "step" : undefined}
                aria-pressed={isSelected}
                aria-label={`${index + 1}. ${step.title}: ${step.statusLabel}`}
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
                  <span className="block break-words text-[11px] leading-tight sm:text-sm">{shortWorkflowStepTitle(step.id)}</span>
                </span>
              </button>
            </li>
          );
        })}
      </ol>

    </section>
  );
}

function shortWorkflowStepTitle(stepId: WorkflowStepId) {
  if (stepId === "scope") return "Zakres";
  if (stepId === "section_map") return "Plan";
  if (stepId === "draft") return "Tekst";
  if (stepId === "review") return "Review";
  return "Dev preview";
}
