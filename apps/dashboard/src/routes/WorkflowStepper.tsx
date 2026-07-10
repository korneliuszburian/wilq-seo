import type { WorkflowStep } from "./contentWorkflowRuntime";

export function WorkflowStepper({ activeIndex, steps }: { activeIndex: number; steps: WorkflowStep[] }) {
  return <ol aria-label="Etapy workflow treści" className="mt-4 grid gap-2 md:grid-cols-4 xl:grid-cols-7">{steps.map((step, index) => { const active = index === activeIndex; const complete = index < activeIndex; return <li key={step.id} className={`rounded-md border px-3 py-2 text-sm ${active ? "border-action bg-action/10 text-action" : complete ? "border-go/30 bg-go/10 text-go" : "border-line bg-surface text-slate-600"}`}><div className="font-semibold">{index + 1}. {workflowStepShortLabel(index, step)}</div><div className="mt-1 text-xs leading-5">{step.statusLabel}</div></li>; })}</ol>;
}
export function workflowStepShortLabel(index: number, step: WorkflowStep) { const labels = ["Preflight", "Plan", "Brief", "Draft", "Review", "WordPress", "Pomiar"]; return labels[index] ?? step.title; }
