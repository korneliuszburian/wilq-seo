import { environmentLabel } from "./contentPageWorkbenchModel";
import type { ContentWorkflowSnapshot } from "./contentWorkflowRuntime";
import { normalizedPath } from "./contentWorkflowTarget";

export function ContentWorkflowJourneyContext({
  data
}: {
  data: ContentWorkflowSnapshot;
}) {
  const item = data.preflight.item;
  const candidate = data.candidate;
  const publicUrl =
    item.source_public_url ?? item.final_canonical_url ?? item.intended_final_url ?? "";
  const pageTitle =
    publicUrl && normalizedPath(publicUrl) === "/"
      ? `Strona główna ${environmentLabel(publicUrl)}`
      : item.wordpress_title_or_h1 ?? item.topic;

  return (
    <section
      aria-label="Kontekst zadania treściowego"
      className="mb-3 rounded-md border border-line bg-white p-3 shadow-sm sm:mb-4 sm:p-4"
    >
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-[minmax(0,1.25fr)_minmax(220px,0.75fr)_minmax(260px,1fr)]">
        <div className="col-span-2 min-w-0 lg:col-span-1">
          <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">Strona</p>
          <h1 className="mt-1 truncate text-xl font-semibold text-ink">{pageTitle}</h1>
          <p className="mt-1 truncate text-xs text-slate-500">{publicUrl || "Brak publicznego URL"}</p>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">Usługa</p>
          <p className="mt-1 text-sm font-semibold text-ink">
            {data.serviceProfileContext.service_label ?? "Nieprzypisana"}
          </p>
          <p className="mt-1 hidden text-xs leading-5 text-slate-600 sm:block">
            {data.serviceProfileContext.status_label}
          </p>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">Decyzja</p>
          <p className="mt-1 text-sm font-semibold text-action">
            {candidate.recommended_mode_label}
          </p>
          <p className="mt-1 hidden max-h-10 overflow-hidden text-xs leading-5 text-slate-600 sm:block">
            {candidate.reason}
          </p>
        </div>
      </div>
    </section>
  );
}
