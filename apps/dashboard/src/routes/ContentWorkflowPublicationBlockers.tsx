import { marketerWorkflowStepTitle, type WorkflowStep } from "./contentWorkflowRuntime";

type ContentWorkflowPublicationBlockersProps = {
  steps: WorkflowStep[];
};

export function ContentWorkflowPublicationBlockers({ steps }: ContentWorkflowPublicationBlockersProps) {
  return (
    <div className="rounded-md border border-line bg-white p-4">
      <h3 className="text-sm font-semibold uppercase tracking-normal text-slate-700">Co blokuje publikację</h3>
      <ul className="mt-3 space-y-3 text-sm leading-6 text-slate-700">
        <li><span className="font-semibold text-ink">Brak zatwierdzenia człowieka.</span> Plan, twierdzenia i paczka szkicu muszą przejść review przed użyciem jako wiedza produkcyjna.</li>
        <li><span className="font-semibold text-ink">WordPress zostaje tylko szkicem.</span> WILQ może przygotować podgląd, ale nie publikuje ani nie nadpisuje strony.</li>
        {steps.slice(0, 3).map((step) => <li key={step.id}><span className="font-semibold text-ink">{marketerWorkflowStepTitle(step.id)}.</span> {step.statusLabel}: {step.summary}</li>)}
      </ul>
      <div className="mt-4 rounded-md border border-wait/30 bg-wait/10 p-3">
        <div className="text-sm font-semibold text-wait">Nie wolno jeszcze twierdzić</div>
        <ul className="mt-2 grid gap-1 text-sm leading-6 text-slate-700 sm:grid-cols-2">
          <li>- automatyczna publikacja</li><li>- wzrost ruchu bez okna pomiaru</li>
          <li>- poprawa pozycji bez obserwacji</li><li>- pełna aktualność twierdzeń bez review</li>
        </ul>
      </div>
    </div>
  );
}
