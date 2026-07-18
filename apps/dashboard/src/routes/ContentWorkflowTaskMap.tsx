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
      className="mb-3 rounded-md border border-line bg-white p-3 shadow-sm sm:mb-4 sm:p-4"
      data-testid="content-workflow-task-map"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            Etap pracy
          </p>
          <h2 id="content-workflow-task-map-title" className="mt-1 text-base font-semibold text-ink">
            {selectedStep.title}
          </h2>
        </div>
        <p className="text-xs text-slate-600">
          Teraz: {currentStep.title}
        </p>
      </div>

      <ol className="mt-3 flex gap-1 overflow-x-auto pb-1" aria-label="Etapy tworzenia treści">
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
                className={`rounded-md border px-2 py-1.5 text-left text-xs font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-60 ${
                  isSelected
                    ? "border-action bg-action/10 text-action"
                    : step.phase === "complete" && step.readiness === "ready"
                      ? "border-go/30 bg-go/5 text-go"
                      : step.readiness === "review_required"
                        ? "border-wait/40 bg-wait/10 text-wait"
                      : "border-line bg-surface text-slate-600"
                }`}
              >
                {index + 1}. {step.title}
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
