import type { ActionPreviewCardViewModel } from "../lib/api";

export function ActionPreviewCard({ card }: { card: ActionPreviewCardViewModel }) {
  return (
    <article className="rounded-md border border-line bg-slate-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-ink">{card.title_label}</h3>
          {card.subtitle_label ? (
            <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
              {card.subtitle_label}
            </p>
          ) : null}
        </div>
        {card.status_label ? (
          <span className="rounded-md border border-line bg-white px-2 py-1 text-xs text-slate-600">
            {card.status_label}
          </span>
        ) : null}
      </div>
      <div className="mt-3 grid gap-1.5 text-xs text-slate-700">
        {card.rows.map((row) => (
          <div key={`${card.id}-${row.label}`}>
            {row.label}: {row.value}
          </div>
        ))}
        {card.apply_state_label ? <div>{card.apply_state_label}</div> : null}
        {card.system_readiness_label ? <div>{card.system_readiness_label}</div> : null}
      </div>
    </article>
  );
}
