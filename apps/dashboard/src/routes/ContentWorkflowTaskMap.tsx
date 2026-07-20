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
      className="wilq-enter wilq-enter-delay-3 mb-3 rounded-md border border-line bg-white p-3 shadow-sm sm:mb-4 sm:p-4"
      data-testid="content-workflow-task-map"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Kolejne etapy workflow
          </p>
          <h2 id="content-workflow-task-map-title" className="mt-1 text-base font-semibold text-ink">
            {selectedStep.title}
          </h2>
        </div>
        <p className="text-xs text-slate-600">
          Teraz: {currentStep.title}
        </p>
      </div>

      <ol className="mt-4 flex gap-2 overflow-x-auto pb-1 lg:grid lg:grid-cols-5 lg:gap-3" aria-label="Etapy tworzenia treści">
        {steps.map((step, index) => {
          const isCurrent = step.id === currentStepId;
          const isSelected = step.id === selectedStepId;
          return (
            <li key={step.id} className="shrink-0">
              <button
                type="button"
                aria-current={isCurrent ? "step" : undefined}
                aria-pressed={isSelected}
                aria-label={`${index + 1}. ${step.title}: ${step.statusLabel}`}
                disabled={!step.canOpen}
                onClick={() => onSelectStep(step.id)}
                className={`flex min-w-36 items-center gap-2 rounded-md border px-2.5 py-2 text-left text-xs font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-60 lg:min-w-0 ${
                  isSelected
                    ? "border-action bg-action/10 text-action"
                    : step.phase === "complete" && step.readiness === "ready"
                      ? "border-go/30 bg-go/5 text-go"
                      : step.readiness === "review_required"
                        ? "border-wait/40 bg-wait/10 text-wait"
                      : "border-line bg-surface text-slate-600"
                }`}
              >
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-current text-xs font-bold">{index + 1}</span>
                <span className="min-w-0">
                  <span className="block truncate text-sm">{shortWorkflowStepTitle(step.id)}</span>
                  <span className="mt-0.5 block truncate text-[11px] font-normal opacity-75">{step.statusLabel}</span>
                </span>
              </button>
            </li>
          );
        })}
      </ol>

      <div className="mt-3 rounded-md border border-action/20 bg-action/5 px-3 py-2">
        <p className="text-xs font-semibold text-slate-500">Następny bezpieczny krok</p>
        {selectedStep.blocker ? (
          <p className="mt-1 text-sm leading-5 text-slate-700" data-testid="selected-step-safe-next-step">
            <span className="font-semibold text-wait" data-testid="selected-step-blocker">
              {selectedStep.blocker.label}
            </span>
            : {selectedStep.safeNextStep}
          </p>
        ) : (
          <p className="mt-1 text-sm leading-5 text-slate-700" data-testid="selected-step-safe-next-step">
            {selectedStep.safeNextStep}
          </p>
        )}
      </div>
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
