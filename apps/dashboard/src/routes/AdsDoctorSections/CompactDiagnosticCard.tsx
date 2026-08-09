import type { ReactNode } from "react";

import { StatusPill } from "../../components/DashboardMockupPrimitives";

export function CompactDiagnosticCard({
  icon,
  title,
  statusLabel,
  summary,
  facts,
  nextStep,
  tone
}: {
  icon: ReactNode;
  title: string;
  statusLabel: string;
  summary: string;
  facts: string[];
  nextStep: string;
  tone: "blue" | "red" | "purple";
}) {
  const toneClasses = {
    blue: "bg-blue-50 text-action",
    red: "bg-red-50 text-risk",
    purple: "bg-violet-50 text-violet-700"
  };

  return (
    <article className="overflow-hidden rounded-md border border-line bg-white shadow-sm">
      <div className="flex items-start justify-between gap-3 border-b border-line px-4 py-3">
        <div className="flex items-center gap-2">
          <span className={`flex size-8 items-center justify-center rounded-md ${toneClasses[tone]}`}>
            {icon}
          </span>
          <h2 className="text-base font-semibold text-ink">{title}</h2>
        </div>
        <StatusPill label={statusLabel} tone={tone === "red" ? "red" : tone} />
      </div>
      <div className="p-4">
        <p className="line-clamp-4 text-sm leading-6 text-slate-700">{summary}</p>
        <div className="mt-4 grid gap-2 sm:grid-cols-3">
          {facts.map((fact) => (
            <div key={fact} className="rounded-md border border-line bg-slate-50 px-3 py-2 text-sm font-medium text-ink">
              {fact}
            </div>
          ))}
        </div>
        <div className="mt-4 border-t border-line pt-3 text-sm leading-6 text-slate-700">
          <span className="font-semibold text-ink">Następny krok: </span>
          {nextStep}
        </div>
      </div>
    </article>
  );
}
