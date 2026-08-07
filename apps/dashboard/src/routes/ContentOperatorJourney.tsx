import { type ContentSelectedWorkspace } from "../lib/api";

type OperatorJourney = ContentSelectedWorkspace["operator_journey"];

export function ContentOperatorJourney({ journey }: { journey: OperatorJourney }) {
  return (
    <div
      aria-label="Ścieżka pracy nad treścią"
      className="mt-4 rounded-2xl border border-line bg-white p-4 shadow-sm"
      data-testid="content-operator-journey"
      role="region"
    >
      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-action">
        Ścieżka pracy
      </p>
      <ol className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
        {journey.steps.map((step, index) => (
          <li
            aria-current={step.phase === "current" ? "step" : undefined}
            className="rounded-xl border border-line bg-surface p-3"
            data-phase={step.phase}
            data-readiness={step.readiness}
            key={step.id}
          >
            <p className="text-xs font-semibold text-slate-500">Krok {index + 1}</p>
            <p className="mt-1 font-semibold text-ink">{step.title}</p>
            <p className="mt-1 text-xs text-slate-600">{step.status_label}</p>
            {step.phase === "current" ? (
              <div className="mt-3 border-t border-line pt-3 text-xs leading-5 text-slate-700">
                <p>{step.summary}</p>
                {step.blocker ? (
                  <div className="mt-2 rounded-lg border border-wait/30 bg-wait/10 p-2">
                    <p className="font-semibold text-ink">{step.blocker.label}</p>
                    <p className="mt-1">{step.blocker.reason}</p>
                  </div>
                ) : null}
                <p className="mt-2 font-medium text-ink">{step.safe_next_step}</p>
              </div>
            ) : null}
          </li>
        ))}
      </ol>
    </div>
  );
}
