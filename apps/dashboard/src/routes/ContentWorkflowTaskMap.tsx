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
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            Przebieg pracy
          </p>
          <h2 id="content-workflow-task-map-title" className="mt-1 text-lg font-semibold text-ink">
            Od decyzji do szkicu na devie
          </h2>
        </div>
        <p className="hidden text-xs text-slate-500 sm:block">
          Bieżący krok: {currentStep.title}
        </p>
      </div>

      <ol className="mt-3 grid grid-cols-5 gap-1.5 sm:gap-2" aria-label="Etapy tworzenia treści">
        {steps.map((step, index) => {
          const isCurrent = step.id === currentStepId;
          const isSelected = step.id === selectedStepId;
          return (
            <li key={step.id} className="min-w-0">
              <button
                type="button"
                aria-current={isCurrent ? "step" : undefined}
                aria-pressed={isSelected}
                aria-label={`${index + 1}. ${step.title}: ${step.statusLabel}`}
                disabled={!step.canOpen}
                onClick={() => onSelectStep(step.id)}
                className={`h-full min-h-16 w-full rounded-md border p-1.5 text-center transition-colors disabled:cursor-not-allowed disabled:opacity-60 sm:min-h-20 sm:p-3 sm:text-left ${
                  isSelected
                    ? "border-action bg-action/10 text-action"
                    : step.phase === "complete" && step.readiness === "ready"
                      ? "border-go/30 bg-go/5 text-go"
                      : step.readiness === "review_required"
                        ? "border-wait/40 bg-wait/10 text-wait"
                      : "border-line bg-surface text-slate-600"
                }`}
              >
                <span className="block text-xs font-semibold uppercase tracking-normal">
                  <span className="sm:hidden">{index + 1}</span>
                  <span className="hidden sm:inline">Krok {index + 1}</span>
                </span>
                <span className="mt-1 block text-[11px] font-semibold leading-4 text-current sm:text-sm">
                  {step.title}
                </span>
                <span className="mt-1 hidden text-xs leading-5 lg:block">{step.statusLabel}</span>
                {isCurrent ? (
                  <span className="mt-1 inline-flex rounded bg-action px-1.5 py-0.5 text-[10px] font-semibold text-white sm:mt-2 sm:px-2 sm:py-1 sm:text-[11px]">
                    Teraz
                  </span>
                ) : null}
              </button>
            </li>
          );
        })}
      </ol>

      <div className="mt-3 grid gap-2 rounded-md border border-line bg-surface p-2 sm:gap-3 sm:p-3 md:grid-cols-[minmax(0,1fr)_minmax(260px,0.8fr)]">
        <div>
          {selectedStep.id !== currentStepId ? (
            <p className="mb-2 text-xs font-semibold text-action">
              Oglądasz ukończony krok. Bieżący krok to: {currentStep.title}.
            </p>
          ) : null}
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-base font-semibold text-ink">{selectedStep.title}</h3>
            <span className="rounded border border-line bg-white px-2 py-1 text-xs font-semibold text-slate-600">
              {selectedStep.statusLabel}
            </span>
          </div>
          <p className="mt-2 hidden text-sm leading-6 text-slate-700 sm:block">
            {selectedStep.summary}
          </p>
        </div>
        <div className="rounded-md border border-action/20 bg-white p-3">
          {selectedStep.blocker ? (
            <>
              <p
                className="text-xs font-semibold uppercase tracking-normal text-wait"
                data-testid="selected-step-blocker"
              >
                {selectedStep.blocker.label}
              </p>
              <p className="mt-1 text-sm leading-5 text-slate-700">
                {selectedStep.blocker.reason}
              </p>
            </>
          ) : (
            <p className="text-xs font-semibold uppercase tracking-normal text-go">
              Krok bez blokady
            </p>
          )}
          <p className="mt-2 text-xs font-semibold uppercase tracking-normal text-slate-500">
            Następny bezpieczny krok
          </p>
          <p
            className="mt-1 text-sm leading-5 text-ink"
            data-testid="selected-step-safe-next-step"
          >
            {selectedStep.safeNextStep}
          </p>
        </div>
      </div>
    </section>
  );
}
