type ContentWorkflowClaimSummaryProps = {
  allowed: number;
  review: number;
  blocked: number;
};

export function ContentWorkflowClaimSummary({ allowed, review, blocked }: ContentWorkflowClaimSummaryProps) {
  return (
    <div className="border-t border-line p-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-normal text-slate-700">Rejestr twierdzeń - skrót</h3>
          <p className="mt-2 text-sm leading-6 text-slate-600">{allowed} do szkicu, {review} wymaga review, {blocked} zablokowane. Szczegóły twierdzeń i surowe dowody są niżej.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <a className="rounded-md border border-line px-3 py-2 text-sm font-semibold text-action" href="#content-workflow-claim-ledger">Otwórz rejestr twierdzeń</a>
          <a className="rounded-md border border-line px-3 py-2 text-sm font-semibold text-action" href="#content-workflow-proof">Otwórz brief</a>
          <a className="rounded-md border border-line px-3 py-2 text-sm font-semibold text-action" href="#content-workflow-wordpress">Pokaż szkic WP</a>
        </div>
      </div>
    </div>
  );
}
