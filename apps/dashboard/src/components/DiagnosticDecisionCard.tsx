import type { ReactNode } from "react";

import { LabelChipRow, MetricTile } from "./OperatorPrimitives";

export function DiagnosticDecisionCard({
  id,
  chips,
  title,
  statusLabel,
  summary,
  rationale,
  nextStep,
  metricTiles,
  children
}: {
  id: string;
  chips: Array<{
    label: string;
    value: number | string | null | undefined;
  }>;
  title: string;
  statusLabel: string;
  summary: string;
  rationale: string;
  nextStep: string;
  metricTiles?: Array<[string, number | string]>;
  children: ReactNode;
}) {
  return (
    <article className="rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <LabelChipRow chips={chips} />
          <h3 className="mt-1 text-base font-semibold">{title}</h3>
        </div>
        <span className="rounded-md border border-line px-2 py-1 text-xs font-semibold text-ink">
          {statusLabel}
        </span>
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-700">{summary}</p>
      <p className="mt-2 text-sm leading-6 text-slate-600">{rationale}</p>
      <p className="mt-3 text-sm font-semibold leading-6 text-ink">{nextStep}</p>
      {metricTiles && metricTiles.length > 0 ? (
        <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
          {metricTiles.map(([label, value]) => (
            <MetricTile key={`${id}-${label}`} label={label} value={value} />
          ))}
        </div>
      ) : null}
      {children}
    </article>
  );
}
