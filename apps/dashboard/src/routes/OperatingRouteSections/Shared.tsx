import type { ReactNode } from "react";

import type { getActionsMutationReadiness } from "../../lib/api";
import { MetricTile } from "../../components/OperatorPrimitives";

export type ActionMutationReadinessSummary = Awaited<
  ReturnType<typeof getActionsMutationReadiness>
>;

export type ActionRow = {
  id: string;
  title: string;
  area: string;
  statusLabel: string;
  statusTone: "green" | "amber" | "red" | "blue" | "purple" | "neutral";
  requires: string;
  nextStep: string;
};

type SurfaceMetric = {
  label: string;
  value: string | number;
};

export function SurfaceIntro({
  title,
  description,
  metrics
}: {
  title: string;
  description: string;
  metrics: SurfaceMetric[];
}) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-normal">{title}</h1>
        <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">{description}</p>
      </div>
      <div className="grid grid-cols-3 gap-2 text-center text-xs">
        {metrics.map((metric) => (
          <MetricTile key={metric.label} label={metric.label} value={metric.value} />
        ))}
      </div>
    </div>
  );
}

export function ToggleButton({ children, onClick }: { children: ReactNode; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex min-h-9 items-center rounded-md border border-line bg-white px-3 py-2 text-xs font-medium text-ink hover:bg-slate-100"
    >
      {children}
    </button>
  );
}
