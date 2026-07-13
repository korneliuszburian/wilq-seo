import type { ContentWorkflowSnapshot } from "./contentWorkflowRuntime";

type MobileContentTriageProps = {
  data: ContentWorkflowSnapshot;
  onOpenDetails: () => void;
};

export function MobileContentTriage({ data, onOpenDetails }: MobileContentTriageProps) {
  const candidate = data.candidate;
  const blockers = candidate.blockers.slice(0, 2);
  return (
    <section aria-label="Mobilny triage treści" className="mb-4 space-y-3">
      <div>
        <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">Treści i SEO · triage</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-ink">Jedna strona na teraz</h1>
        <p className="mt-2 text-sm leading-6 text-slate-600">Najpierw podejmij decyzję dla wybranej strony. Szczegóły otworzysz niżej.</p>
      </div>
      <article className="rounded-md border border-action/30 bg-white p-4 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-normal text-action">Decyzja</p>
        <h2 className="mt-2 text-lg font-semibold leading-6 text-ink">{candidate.title}</h2>
        <p className="mt-3 line-clamp-4 text-sm leading-6 text-slate-700">{candidate.reason}</p>
        <p className="mt-3 line-clamp-3 text-sm font-semibold leading-6 text-ink">{candidate.safe_next_step}</p>
        <button type="button" onClick={onOpenDetails} className="mt-4 inline-flex h-11 w-full items-center justify-center rounded-md bg-action px-4 text-sm font-semibold text-white">
          Otwórz szczegóły pracy
        </button>
      </article>
      <div className="rounded-md border border-wait/30 bg-wait/10 p-4">
        <h2 className="text-sm font-semibold text-ink">Dwie najważniejsze blokady</h2>
        {blockers.length ? (
          <ul className="mt-3 space-y-3">
            {blockers.map((blocker) => (
              <li key={blocker.code} className="text-sm leading-5 text-slate-700">
                <span className="font-semibold text-ink">{blocker.label}</span>
                <span className="mt-1 block">{blocker.reason}</span>
              </li>
            ))}
          </ul>
        ) : <p className="mt-2 text-sm leading-6 text-slate-700">Brak dodatkowych blokad dla tej decyzji.</p>}
      </div>
      <details className="rounded-md border border-line bg-white px-3 py-2 text-sm">
        <summary className="cursor-pointer font-semibold text-action">Pokaż dowody i świeżość</summary>
        <div className="mt-3 space-y-2 text-xs leading-5 text-slate-600">
          <p>Świeżość: {data.freshnessAssessment.state_label}</p>
          <p>Dowody źródłowe: {candidate.evidence_ids.length}</p>
          <p>Źródła: {candidate.source_connectors.join(", ")}</p>
        </div>
      </details>
    </section>
  );
}
