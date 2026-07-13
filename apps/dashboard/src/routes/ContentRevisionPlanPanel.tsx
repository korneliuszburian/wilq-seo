import { FileText } from "lucide-react";

import type { ContentWorkItemRevisionPlanResponse } from "../lib/api";

export function ContentRevisionPlanPanel({
  plan,
  safetyText
}: {
  plan: ContentWorkItemRevisionPlanResponse["revision_plan"] | null;
  safetyText: string;
}) {
  const firstInstruction = plan?.instructions[0] ?? null;
  const firstBlocker = plan?.blockers[0] ?? null;
  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="flex items-start gap-3">
        <div className="rounded-md border border-line bg-surface p-2 text-action"><FileText aria-hidden="true" size={18} /></div>
        <div>
          <h2 className="text-sm font-semibold text-ink">Plan poprawki</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">{safetyText}</p>
          {firstBlocker ? <div className="mt-3 rounded-md border border-line bg-surface p-3 text-sm"><div className="font-semibold text-ink">{firstBlocker.label}</div><p className="mt-2 leading-6 text-slate-700">{firstBlocker.reason}</p><p className="mt-2 text-xs text-slate-500">{firstBlocker.next_step}</p></div> : null}
          {firstInstruction ? <div className="mt-3 rounded-md border border-line bg-surface p-3 text-sm"><div className="font-semibold text-ink">{firstInstruction.change}</div><p className="mt-2 leading-6 text-slate-700">{firstInstruction.reason}</p>{firstInstruction.required_evidence_ids.length ? <p className="mt-2 text-xs text-slate-500">Wymagane dowody: {firstInstruction.required_evidence_ids.join(", ")}</p> : null}</div> : null}
        </div>
      </div>
    </section>
  );
}
