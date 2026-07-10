import { CheckCircle2 } from "lucide-react";
import type { WorkflowStep } from "./contentWorkflowRuntime";

export function WorkflowStepsList({ steps }: { steps: WorkflowStep[] }) {
  return <ol aria-label="Kroki workflow treści" className="grid gap-3 lg:grid-cols-3">{steps.map((step) => <li key={step.title} className="rounded-md border border-line bg-white p-4"><div className="flex items-start gap-3"><div className="mt-0.5 rounded-md border border-line bg-surface p-2 text-action"><CheckCircle2 aria-hidden="true" size={18} /></div><div><h2 className="text-sm font-semibold text-ink">{step.title}</h2><div className="mt-1 text-xs font-medium uppercase tracking-normal text-slate-500">{step.statusLabel}</div><p className="mt-2 text-sm leading-6 text-slate-600">{step.summary}</p></div></div></li>)}</ol>;
}
