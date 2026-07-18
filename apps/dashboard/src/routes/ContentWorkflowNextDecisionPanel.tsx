import { ContentWorkflowFactTile as FactTile } from "./ContentWorkflowFactTile";

type ContentWorkflowNextDecisionPanelProps = {
  activeStepLabel: string;
  decisionTitle: string;
  decisionReason: string;
  evidenceCount: number;
  reviewClaims: number;
  blockedClaims: number;
  nextStep: string;
};

export function ContentWorkflowNextDecisionPanel({
  activeStepLabel,
  decisionTitle,
  decisionReason,
  evidenceCount,
  reviewClaims,
  blockedClaims,
  nextStep
}: ContentWorkflowNextDecisionPanelProps) {
  return (
    <div className="rounded-md border border-line bg-surface p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold uppercase tracking-normal text-slate-700">Następny krok</h3>
        <span className="rounded-md bg-action/10 px-2 py-1 text-xs font-semibold text-action">Aktywny krok: {activeStepLabel}</span>
      </div>
      <p className="mt-3 text-base font-semibold leading-6 text-ink">{decisionTitle}</p>
      <p className="mt-2 text-sm leading-6 text-slate-700">{decisionReason}</p>
      <div className="mt-4 grid gap-2 md:grid-cols-3">
        <FactTile label="Dowody WILQ" value={`${evidenceCount}`} />
        <FactTile label="Twierdzenia do review" value={`${reviewClaims}`} />
        <FactTile label="Twierdzenia zablokowane" value={`${blockedClaims}`} />
      </div>
      <div className="mt-4"><div className="text-sm font-semibold text-ink">Następny krok</div><p className="mt-1 text-sm leading-6 text-slate-700">{nextStep}</p></div>
      <div className="mt-4 flex flex-wrap gap-3">
        <a className="inline-flex items-center rounded-md bg-action px-4 py-2 text-sm font-semibold text-white" href="#content-workflow-actions">Przejdź do decyzji</a>
        <a className="inline-flex items-center rounded-md border border-action/40 px-4 py-2 text-sm font-semibold text-action" href="#content-workflow-proof">Pokaż źródła</a>
      </div>
    </div>
  );
}
