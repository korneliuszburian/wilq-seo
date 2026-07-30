import type { DiagnosticDataReadiness } from "../lib/api";
import type { ReactNode } from "react";

import { MetricFactChips } from "./MetricFactChips";

export function DiagnosticDataReadinessPanel({
  readiness
}: {
  readiness: DiagnosticDataReadiness;
}) {
  const canShowFacts = readiness.state === "ready" || readiness.state === "partial";

  return (
    <section
      aria-label="Gotowość danych diagnostycznych"
      className="mb-6 rounded-md border border-line bg-white p-4"
      data-testid="diagnostic-data-readiness"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-normal text-slate-600">
            Dane do decyzji
          </p>
          <h2 className="mt-1 text-lg font-semibold text-ink">{readiness.state_label}</h2>
        </div>
        <span className="rounded bg-slate-100 px-2 py-1 text-xs text-slate-700">
          Źródło: {readiness.connector_label}
        </span>
      </div>
      <p className="mt-2 text-sm leading-6 text-slate-700">{readiness.reason}</p>
      <p className="mt-1 text-sm leading-6 text-slate-600">{readiness.coverage_label}</p>
      <p className="mt-2 text-sm font-medium text-ink">{readiness.safe_next_step}</p>
      {readiness.refresh_allowed && !canShowFacts ? (
        <a className="mt-3 inline-flex text-sm font-medium text-action hover:underline" href="/settings">
          Sprawdź źródło danych
        </a>
      ) : null}
      {canShowFacts ? <MetricFactChips facts={readiness.factual_metrics} /> : null}
    </section>
  );
}

export function DiagnosticDataReadinessGate({
  readiness,
  children
}: {
  readiness: DiagnosticDataReadiness;
  children: ReactNode;
}) {
  return (
    <>
      <DiagnosticDataReadinessPanel readiness={readiness} />
      {readiness.state === "ready" ? children : null}
    </>
  );
}
