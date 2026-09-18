import type { DiagnosticDataReadiness } from "@wilq/shared-schemas";

export function DiagnosticDataReadinessPanel({
  readiness
}: {
  readiness: DiagnosticDataReadiness;
}) {
  return (
    <section
      aria-label="Gotowość danych diagnostycznych"
      className="mb-6 rounded-md border border-line bg-white p-4"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            Gotowość danych diagnostycznych
          </p>
          <h2 className="mt-1 text-lg font-semibold text-ink">{readiness.state_label}</h2>
        </div>
        <span className="rounded-md border border-line bg-slate-50 px-2 py-1 text-xs text-slate-600">
          {readiness.connector_label}
        </span>
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-700">{readiness.reason}</p>
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <div className="rounded-md border border-line bg-slate-50 p-3">
          <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            Zakres danych
          </p>
          <p className="mt-1 text-sm leading-6 text-slate-700">{readiness.coverage_label}</p>
        </div>
        <div className="rounded-md border border-line bg-slate-50 p-3">
          <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            Bezpieczny następny krok
          </p>
          <p className="mt-1 text-sm font-medium leading-6 text-ink">
            {readiness.safe_next_step}
          </p>
        </div>
      </div>
    </section>
  );
}
