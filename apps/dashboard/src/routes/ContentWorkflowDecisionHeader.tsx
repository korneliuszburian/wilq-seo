import { marketerWorkflowStepTitle, type WorkflowStepId } from "./contentWorkflowRuntime";

type ContentWorkflowDecisionHeaderProps = {
  topic: string;
  currentStepId: WorkflowStepId;
};

export function ContentWorkflowDecisionHeader({ topic, currentStepId }: ContentWorkflowDecisionHeaderProps) {
  return (
    <div className="border-b border-line p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-xs font-semibold uppercase tracking-normal text-action">Workflow treści: jeden aktywny krok</div>
          <h2 className="mt-1 text-lg font-semibold tracking-normal text-ink">{topic}</h2>
          <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-700">Status: plan wymaga Twojej decyzji. Zapis szkicu do WordPress pozostanie niedostępny, dopóki treść, źródła i sprawdzenie człowieka nie będą gotowe.</p>
        </div>
        <div className="rounded-md border border-wait/30 bg-wait/10 px-3 py-2 text-sm font-semibold text-wait">Szkic jeszcze niegotowy</div>
      </div>
      <div
        className="mt-4 flex flex-wrap items-center gap-2 rounded-md border border-line bg-surface px-3 py-2 text-sm"
        data-testid="technical-workflow-state"
      >
        <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Stan pracy</span>
        <span className="font-semibold text-ink">{marketerWorkflowStepTitle(currentStepId)}</span>
        <span className="text-slate-500">Plan i struktura są stanem systemowym, nie osobnym approvalu.</span>
      </div>
    </div>
  );
}
